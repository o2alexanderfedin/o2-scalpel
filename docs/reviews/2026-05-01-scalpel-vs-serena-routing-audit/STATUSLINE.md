---
title: o2-scalpel update indicator — status-line setup
date: 2026-05-01
author: AI Hive(R)
parent: ./REPORT.md
---

# Wire the o2-scalpel update indicator into your Claude Code status line

The v1.11 generator (engine commit `8d27ae4d`) ships a tiny POSIX-shell script with every o2-scalpel plugin that emits a yellow `⬆ /o2-scalpel-update` segment when an engine update is available, and nothing otherwise. The cache is refreshed in the background by a SessionStart hook (one network call per 6 hours, shared across all enabled scalpel-* plugins) and cleared automatically when you run `/o2-scalpel-update`.

To wire it in, add a `statusLine` section to `~/.claude/settings.json` pointing at any installed scalpel-* plugin's copy of the script. All 23 plugin copies are byte-identical so you can pick whichever plugin you have enabled.

## One-time setup

```jsonc
// ~/.claude/settings.json
{
  // ... existing settings ...
  "statusLine": {
    "type": "command",
    "command": "${HOME}/.claude/plugins/marketplaces/o2-scalpel/o2-scalpel-markdown/hooks/scalpel-statusline.sh"
  }
}
```

If you already have a `statusLine` (e.g. for `gsd`), wrap them together:

```jsonc
"statusLine": {
  "type": "command",
  "command": "node ~/.claude/hooks/gsd-statusline.js && ~/.claude/plugins/marketplaces/o2-scalpel/o2-scalpel-markdown/hooks/scalpel-statusline.sh"
}
```

(Each script writes a single line to stdout; concatenated output is what Claude Code displays.)

## How it works (data flow)

1. **SessionStart hook** (`hooks/check-scalpel-update.sh`, fires automatically when any scalpel-* plugin loads). Probes `git ls-remote https://github.com/o2alexanderfedin/o2-scalpel-engine.git HEAD`. Writes `~/.cache/o2-scalpel/update-check.json`:
   ```json
   {"update_available": true, "installed_sha": "8d27ae4d…", "upstream_sha": "<latest>", "checked": 1788…}
   ```
   Throttled to 1 call per 6h so multiple sessions don't hammer GitHub.

2. **Status-line script** (`hooks/scalpel-statusline.sh`, runs on every Claude Code status-line tick). `grep`s the cache JSON for `"update_available":true`. If found, prints:
   ```
   ⬆ /o2-scalpel-update
   ```
   in ANSI yellow; otherwise empty. Pure shell, no Python, no uvx — completes in < 5 ms.

3. **Slash command** (`/o2-scalpel-update`, runs on demand). Calls `uvx --refresh --from git+https://… scalpel --version` to force the uvx cache to re-resolve and rebuild against upstream HEAD. Writes the new SHA to `~/.cache/o2-scalpel/installed-sha` and updates `update-check.json` so the status-line indicator clears immediately.

## Cache files

| Path | Written by | Read by |
|---|---|---|
| `~/.cache/o2-scalpel/update-check.json` | `check-scalpel-update.sh`, `/o2-scalpel-update` | `scalpel-statusline.sh` |
| `~/.cache/o2-scalpel/installed-sha` | `/o2-scalpel-update` (and seeded by `check-scalpel-update.sh` on first run) | `check-scalpel-update.sh` |

Both files are owned by your user. To force a re-check before the 6h throttle expires:
```bash
rm ~/.cache/o2-scalpel/update-check.json
# … then start a new Claude Code session, or just wait for SessionStart on next plugin load.
```

## Disable the indicator

Either remove the `statusLine` line from `~/.claude/settings.json`, OR delete the cache:
```bash
rm -rf ~/.cache/o2-scalpel/
```
(The cache will regenerate next time SessionStart fires; deleting it is a way to suppress one cycle.)

## Pattern reference

This mirrors the `gsd` (`get-shit-done`) update-indicator pattern at:
- `~/.claude/hooks/gsd-statusline.js` (status-line emitter)
- `~/.claude/hooks/gsd-check-update.js` (SessionStart background probe)
- `~/.cache/gsd/gsd-update-check.json` (shared cache schema)

The schemas are intentionally similar so the same mental model applies.
