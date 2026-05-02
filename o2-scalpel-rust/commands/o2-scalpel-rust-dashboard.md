---
description: Open the o2-scalpel-rust engine dashboard in your browser (auto-discovers the port)
allowed-tools: ["Bash(pgrep:*)", "Bash(lsof:*)", "Bash(awk:*)", "Bash(tr:*)", "Bash(sed:*)", "Bash(curl:*)", "Bash(open:*)", "Bash(uname:*)", "Bash(xdg-open:*)"]
---

# /o2-scalpel-rust-dashboard

Open the dashboard for the **`scalpel-rust`** MCP server (the o2-scalpel-rust plugin's engine instance). Discovery: `pgrep -f "scalpel-rust"` cross-referenced against `lsof -iTCP -sTCP:LISTEN` to resolve the port.

The engine binds the dashboard **lazily** — until the agent makes its first `scalpel_*` tool call against the rust server, no port is bound. If discovery says "not yet bound", invoke any rust facade (e.g. `scalpel_workspace_health`) and re-run.

!`PIDS_RE=$(pgrep -f "start-mcp-server.*--server-name scalpel-rust" 2>/dev/null | tr '\n' '|' | sed 's/|$//'); if [ -z "$PIDS_RE" ]; then echo "✗ scalpel-rust MCP server is not running."; echo "  Enable it via /plugins (look for o2-scalpel-rust@o2-scalpel) or in your Claude Code settings, then restart this session."; exit 0; fi; PORT=$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk -v re="^(${PIDS_RE})$" '$2 ~ re { n=split($9,a,":"); print a[n]; exit }'); if [ -z "$PORT" ]; then echo "✓ scalpel-rust MCP server is running (PIDs: ${PIDS_RE//|/, })"; echo "✗ but its dashboard hasn't bound a port yet."; echo "  The engine binds the dashboard lazily — invoke any scalpel_* tool against the rust server first, then re-run this command."; exit 0; fi; URL="http://127.0.0.1:${PORT}/dashboard/"; HEARTBEAT="http://127.0.0.1:${PORT}/heartbeat"; if ! curl -fsS -o /dev/null -m 2 "$HEARTBEAT"; then echo "✗ Found scalpel-rust listening on port ${PORT} but /heartbeat is not responding."; exit 0; fi; echo "✓ scalpel-rust dashboard at $URL"; case "$(uname -s)" in Darwin) open "$URL" ;; Linux) xdg-open "$URL" 2>/dev/null || echo "(xdg-open missing — open the URL manually)" ;; *) echo "(open the URL in your browser manually)" ;; esac`
