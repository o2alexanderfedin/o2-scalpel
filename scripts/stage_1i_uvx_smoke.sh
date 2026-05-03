#!/usr/bin/env bash
# Stage 1I - uvx --from <local-path> smoke for one language.
#
# Usage:    scripts/stage_1i_uvx_smoke.sh <language>
# Stdout:   one tool name per line (the response of tools/list).
# Stderr:   diagnostic chatter from uvx + the launched MCP server.
# Exit:     0 on success; non-zero on any failure.

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <language>" >&2
  exit 64
fi
LANG_ARG="$1"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_DIR="${REPO_ROOT}/o2-scalpel-${LANG_ARG}"
MCP_JSON="${PLUGIN_DIR}/.mcp.json"

if [ ! -f "${MCP_JSON}" ]; then
  echo "smoke: missing ${MCP_JSON} - has T1/T2 run?" >&2
  exit 65
fi

# v2.0 wire-name cleanup (spec docs/superpowers/specs/2026-05-03-v2.0-mcp-wire-name-cleanup-spec.md
# §5.2): the `.mcp.json` server JSON-key is the constant "lsp", but the
# CLI ``--server-name`` arg is per-language ``scalpel-<lang>``. Confirm both.
SERVER_KEY=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); k=[k for k in d['mcpServers']]; assert len(k)==1, k; print(k[0])" "${MCP_JSON}")
if [ "${SERVER_KEY}" != "lsp" ]; then
  echo "smoke: unexpected mcpServers JSON-key '${SERVER_KEY}' (want 'lsp')" >&2
  exit 66
fi
CLI_SERVER_NAME=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); a=d['mcpServers']['lsp']['args']; print(a[a.index('--server-name')+1])" "${MCP_JSON}")
if [ "${CLI_SERVER_NAME}" != "scalpel-${LANG_ARG}" ]; then
  echo "smoke: unexpected --server-name CLI arg '${CLI_SERVER_NAME}' (want 'scalpel-${LANG_ARG}')" >&2
  exit 66
fi

# Build the JSON-RPC tools/list request. Newline-delimited per MCP stdio framing.
REQUEST=$(printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"stage-1i-smoke","version":"0.0.1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}')

# Launch the server via uvx --from <repo-root>. The published .mcp.json files
# invoke `serena start-mcp-server --server-name scalpel-<lang>`; we match that
# contract here so the smoke test covers what users actually run.
# (`serena-mcp` was a console-script in pre-eb453976 versions; upstream
# replaced it with the `start-mcp-server` subcommand.)
STDERR_LOG="/tmp/stage_1i_mcp.${LANG_ARG}.stderr"
RESPONSE=$(printf '%s' "${REQUEST}" \
  | timeout 30 uvx --from "${REPO_ROOT}/vendor/serena" serena start-mcp-server --server-name "scalpel-${LANG_ARG}" 2>"${STDERR_LOG}" \
  || { echo "smoke: uvx run failed (exit $?). stderr saved at ${STDERR_LOG}" >&2; exit 67; })

# Parse the tools/list response (id == 2) and emit tool names one per line.
echo "${RESPONSE}" | python3 -c "
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    if msg.get('id') == 2 and 'result' in msg:
        for tool in msg['result'].get('tools', []):
            print(tool['name'])
        sys.exit(0)
print('smoke: no tools/list response received', file=sys.stderr)
sys.exit(68)
"
