---
title: o2-scalpel update indicator — status-line setup
date: 2026-05-01
author: AI Hive(R)
parent: ./REPORT.md
---

# Wire the o2-scalpel update indicator into your Claude Code status line

When an `o2-scalpel-engine` update is available, your Claude Code status line can show a yellow `⬆ /o2-scalpel-update` segment so you know to run the update command. This page walks through the recommended setup and explains why the recipe is uninstall-safe.

> **What changed in v1.12 (2026-05-01):** the update cache moved from `~/.cache/o2-scalpel/` (where it leaked forever after plugin uninstall) to `${CLAUDE_PLUGIN_DATA}/update-cache/` (Claude Code's per-plugin scratch dir, auto-cleaned on uninstall). The recommended `statusLine.command` is now an inline shell snippet that reads from a glob across plugin data dirs — so it has zero dependency on any specific plugin path. **If you wired the v1.11 recipe, please follow the migration note at the bottom.**

## One-time setup (uninstall-safe)

Add a `statusLine` section to `~/.claude/settings.json`:

```jsonc
// ~/.claude/settings.json
{
  // ... existing settings ...
  "statusLine": {
    "type": "command",
    "command": "F=$(find $HOME/.claude/plugins/data -maxdepth 3 -path '*o2-scalpel-*/update-cache/update-check.json' -print -quit 2>/dev/null); [ -n \"$F\" ] && grep -q '\"update_available\":true' \"$F\" && printf '\\033[33m\\xe2\\xac\\x86 /o2-scalpel-update\\033[0m'"
  }
}
```

Why this form:

- **No dependency on any plugin tree path** — pure inline shell that reads only the cache file.
- **Self-healing on uninstall** — if you uninstall every scalpel-* plugin, `find` finds no matches and the status line prints empty (no errors, no broken-path warnings, no glob-expansion warnings under zsh).
- **Survives plugin reinstall** — `find` automatically picks up whichever plugin owns a fresh cache.
- **No external script** — nothing to copy to `~/.claude/scripts/`; the entire status-line logic lives in your settings.json.
- **Portable across shells** (bash, zsh, sh) — `find` doesn't trigger shell glob expansion, so it works whether Claude Code's status-line runner shells out via `/bin/sh`, the user's `$SHELL`, or anything else.

Combine with `gsd` or any other status-line emitter by chaining commands:

```jsonc
"statusLine": {
  "type": "command",
  "command": "node ~/.claude/hooks/gsd-statusline.js && (F=$(find $HOME/.claude/plugins/data -maxdepth 3 -path '*o2-scalpel-*/update-cache/update-check.json' -print -quit 2>/dev/null); [ -n \"$F\" ] && grep -q '\"update_available\":true' \"$F\" && printf '\\033[33m\\xe2\\xac\\x86 /o2-scalpel-update\\033[0m')"
}
```

## How it works (data flow)

1. **SessionStart hook** (`hooks/check-scalpel-update.sh`, fires automatically when any scalpel-* plugin loads). Probes `git ls-remote https://github.com/o2alexanderfedin/o2-scalpel-engine.git HEAD`. Writes `${CLAUDE_PLUGIN_DATA}/update-cache/update-check.json`:
   ```json
   {"update_available": true, "installed_sha": "<old>", "upstream_sha": "<latest>", "checked": 1788…}
   ```
   Throttled per-plugin to 1 call per 6h. With N enabled scalpel-* plugins, worst case is N independent calls per 6h (each plugin throttles its own cache).

2. **Status-line script / inline snippet** runs on every Claude Code status-line tick (~every few seconds). Globs `~/.claude/plugins/data/o2-scalpel-*/update-cache/update-check.json` and reads the first match. If `"update_available":true`, prints `⬆ /o2-scalpel-update` in ANSI yellow; else nothing. Pure shell, completes in < 5 ms.

3. **Slash command** (`/o2-scalpel-update`, runs on demand). Calls `uvx --refresh --from git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git scalpel --version` to force the uvx cache to re-resolve. Then writes `update_available:false` to **every** installed scalpel-* plugin's cache (not just one) so the status-line indicator clears for all of them in one go.

## Cache files

| Path | Owner | Auto-cleaned on uninstall? |
|---|---|---|
| `${CLAUDE_PLUGIN_DATA}/update-cache/update-check.json` (one per enabled scalpel-* plugin, e.g. `~/.claude/plugins/data/o2-scalpel-rust/update-cache/update-check.json`) | Plugin runtime | ✅ Yes — Claude Code wipes `${CLAUDE_PLUGIN_DATA}/` on uninstall |
| `${CLAUDE_PLUGIN_DATA}/update-cache/installed-sha` | Plugin runtime | ✅ Yes — same |

To force a re-check before the 6h throttle expires:
```bash
rm ~/.claude/plugins/data/o2-scalpel-*/update-cache/update-check.json
# Start a new Claude Code session, or wait for SessionStart on next plugin load.
```

## Disable the indicator

Two options:

- **Just hide it** — remove the `statusLine` line from `~/.claude/settings.json`. Cache files keep getting written but nothing reads them; cost is zero.
- **Stop the writer too** — disable all scalpel-* plugins via `/plugins`. Their SessionStart hooks no longer fire, so the cache stops being refreshed. (Note: per Claude Code GH#35713, disabled plugins continue firing hooks until session restart — you may need to restart Claude Code after disabling.)

## Migration from v1.11 (2026-04-30 → 2026-05-01)

If you wired the v1.11 recipe (which pointed `statusLine.command` at a path inside the plugin tree like `~/.claude/plugins/marketplaces/o2-scalpel/o2-scalpel-markdown/hooks/scalpel-statusline.sh`), please replace that with the new inline form above.

Two things changed:

1. **Cache path moved** from `~/.cache/o2-scalpel/` to `${CLAUDE_PLUGIN_DATA}/update-cache/`. The slash command auto-removes the legacy `~/.cache/o2-scalpel/` on first run, so once you run `/o2-scalpel-update` once you're fully migrated.
2. **Recommended `statusLine.command` is now inline** — independent of plugin tree paths, survives uninstall.

If you don't migrate, the old v1.11 path in your settings.json will start failing silently on every status-line tick after you upgrade plugins (because the v1.12 plugin tree no longer ships scripts that read the legacy `~/.cache/o2-scalpel/`). Migration is a one-line edit.

## Pattern reference

This mirrors the `gsd` (`get-shit-done`) update-indicator pattern at:
- `~/.claude/hooks/gsd-statusline.js` (status-line emitter)
- `~/.claude/hooks/gsd-check-update.js` (SessionStart background probe)
- `~/.cache/gsd/gsd-update-check.json` (shared cache schema)

The cache JSON schema is intentionally aligned with gsd so the mental model carries over.

## Why not declare the statusLine in plugin.json?

Looked into this in the v1.12 lifecycle research (2026-05-01). Findings:

- `statusLine.command` is **user-only** in Claude Code's settings schema — plugins cannot ship a `statusLine` field in `plugin.json`. (Source: docs.claude.com/docs/en/plugins-reference, line ~697 — plugin-shipped settings.json supports only `agent` and `subagentStatusLine`.)
- No `PreUninstall` / `PostUninstall` lifecycle hooks exist either (GH#11240, feature request, not shipped).

So we can't auto-set the statusLine on install or auto-clean it on uninstall. The inline-shell recipe + plugin-data cache migration is the cleanest workaround given current Claude Code capabilities.
