---
description: Open the o2-scalpel-haxe engine dashboard in your browser (auto-discovers the port)
allowed-tools: ["Bash(pgrep:*)", "Bash(lsof:*)", "Bash(grep:*)", "Bash(tr:*)", "Bash(sed:*)", "Bash(curl:*)", "Bash(open:*)", "Bash(uname:*)", "Bash(xdg-open:*)"]
---

# /o2-scalpel-haxe-dashboard

Open the dashboard for the **`scalpel-haxe`** MCP server (the o2-scalpel-haxe plugin's engine instance). Discovery: `pgrep -f "scalpel-haxe"` cross-referenced against `lsof -iTCP -sTCP:LISTEN` to resolve the port.

The engine binds the dashboard **lazily** — until the agent makes its first Scalpel tool call against the haxe server, no port is bound. If discovery says "not yet bound", invoke any haxe facade (e.g. `workspace_health`) and re-run.

!`PIDS_CSV=$(pgrep -f "start-mcp-server.*--server-name scalpel-haxe" 2>/dev/null | tr '\n' ',' | sed 's/,$//'); if [ -z "$PIDS_CSV" ]; then echo "✗ scalpel-haxe MCP server is not running."; echo "  Enable it via /plugins (look for o2-scalpel-haxe@o2-scalpel) or in your Claude Code settings, then restart this session."; exit 0; fi; PORT=$(lsof -a -nP -iTCP -sTCP:LISTEN -p "$PIDS_CSV" 2>/dev/null | grep -oE ':[0-9]+ \(LISTEN\)' | head -1 | tr -dc '0-9'); PIDS_HUMAN=${PIDS_CSV//,/, }; if [ -z "$PORT" ]; then echo "✓ scalpel-haxe MCP server is running (PIDs: $PIDS_HUMAN)"; echo "✗ but its dashboard hasn't bound a port yet."; echo "  The engine binds the dashboard lazily — invoke any Scalpel tool against the haxe server first, then re-run this command."; exit 0; fi; URL="http://127.0.0.1:${PORT}/dashboard/"; HEARTBEAT="http://127.0.0.1:${PORT}/heartbeat"; if ! curl -fsS -o /dev/null -m 2 "$HEARTBEAT"; then echo "✗ Found scalpel-haxe listening on port ${PORT} but /heartbeat is not responding."; exit 0; fi; echo "✓ scalpel-haxe dashboard at $URL"; case "$(uname -s)" in Darwin) open "$URL" ;; Linux) xdg-open "$URL" 2>/dev/null || echo "(xdg-open missing — open the URL manually)" ;; *) echo "(open the URL in your browser manually)" ;; esac`
