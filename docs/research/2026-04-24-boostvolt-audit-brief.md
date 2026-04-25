# boostvolt/claude-code-lsps — Code Audit

## Repo shape

**Total LoC**: 2,381 lines across JSON, shell scripts, and Markdown

**File breakdown**:
- 22 × `.lsp.json` files (220 lines total, ~10 lines each)
- 22 × `hooks.json` files (~330 lines)
- 22 × `check-*.sh` hook scripts (~550 lines)
- 22 × `.claude-plugin/plugin.json` files (242 lines, ~11 lines each, all identical)
- 1 × `.claude-plugin/marketplace.json` (259 lines)
- 2 × README/CLAUDE.md documentation files (~1,400 lines)

**Plugin count**: 22 language servers, all present in the repo

**Repo architecture**: Flat marketplace of identical plugin structures; no plugin-level customization beyond LSP command/args.

---

## Plugin manifest schema (representative)

### `.claude-plugin/plugin.json`
All 22 plugins use identical structure (11 lines each):
```json
{
  "name": "<plugin-name>",
  "description": "<language> language server",
  "version": "1.0.0",
  "author": { "name": "Jan Kott" },
  "license": "MIT",
  "repository": "https://github.com/boostvolt/claude-code-lsps",
  "homepage": "https://github.com/boostvolt/claude-code-lsps"
}
```

**Fields present**: `name`, `description`, `version`, `author`, `license`, `repository`, `homepage`

**Fields absent**: No custom capabilities, no skill/command refs, no MCP refs, no capability flags

### `.lsp.json` schema
**Required fields** (all plugins implement):
- `command`: LSP server binary to execute
- `extensionToLanguage`: Maps file extensions to LSP language IDs

**Optional fields used in this repo**:
- `args`: String array (used by ~8 plugins: omnisharp, intelephense, pyright, vtsls, etc.)
- `env`: Not observed
- `initializationOptions`: Not observed
- `settings`: Not observed
- `transport`, `workspaceFolder`, `startupTimeout`, `shutdownTimeout`, `restartOnCrash`, `maxRestarts`: Not observed

**Example** (rust-analyzer):
```json
{
  "rust": {
    "command": "rust-analyzer",
    "extensionToLanguage": { ".rs": "rust" }
  }
}
```

**Example with args** (omnisharp):
```json
{
  "csharp": {
    "command": "OmniSharp",
    "args": ["-lsp"],
    "extensionToLanguage": { ".cs": "csharp", ".csx": "csharp" }
  }
}
```

---

## What every plugin contains today

| Plugin | Has hooks? | Has commands? | Has agents? | Has skills? | Has MCP? | Has helpers? |
|--------|-----------|---------------|-----------|-----------|---------|--------------|
| All 22 | YES | NO | NO | NO | NO | NO |

**Hooks**: Every plugin has `hooks/hooks.json` (runs SessionStart) + `hooks/check-<name>.sh` (auto-install binary)
- Hook type: `command` only
- Hook timeout: 30–60 seconds
- Hook purpose: Binary existence check, brew/package-manager auto-install, PATH instructions

**No other extension slots**: Confirmed zero `/commands`, `/agents`, `/skills`, `/mcp_servers` directories anywhere in the repo.

---

## Extension slots NOT currently used by ANY plugin

| Slot | Availability | Could carry write capability? |
|------|--------------|------------------------------|
| Slash commands | `.claude-plugin/commands/` + command.json | YES—could invoke codeAction, rename, documentLink |
| Subagents | `.claude-plugin/agents/` + agent.json | YES—could apply edit workflows |
| Skills | `.claude-plugin/skills/` + skill.json | YES—could expose codeAction/rename/formatting as tools |
| MCP servers | `.claude-plugin/mcp_servers/` + mcp config | YES—could proxy LSP write methods |
| LSP initializationOptions | `.lsp.json` field | MAYBE—only for server-side capability negotiation |
| LSP settings | `.lsp.json` field | MAYBE—only for diagnostic/analysis config |

**LSP read-only constraint**: The Claude Code built-in LSP tool exposes only **9 operations**, all read-only:
- `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls`

Write methods (`codeAction`, `rename`, `formatting`, `documentLink`, `willSave/didSave`, `applyEdit`) are **not exposed** by the LSP tool itself.

---

## Write-related artifacts found

**ZERO mentions of**:
- `applyEdit`, `codeAction`, `rename`, `refactor`, `formatting`, `willSave`, `didSave`, `documentLink`, `workspace/applyEdit`

**Search performed**: `grep -ri "applyEdit\|codeAction\|refactor\|rename\|willSave\|didSave\|write"` across JSON, MD, and SH files → no matches

**Implication**: No experimental branches, draft PRs, docs, or helper code for write support exist anywhere.

---

## Maintainer signals

From `CLAUDE.md` (lines 50–60):
> **Debug Logging**: Plugins that support args/env-based logging should include `loggingConfig`
> - Use `${CLAUDE_PLUGIN_LSP_LOG_FILE}` for log file paths.
> 
> **References**:
> - [Official LSP docs](https://code.claude.com/docs/en/plugins-reference#lsp-servers)
> - Requires Claude Code 2.0.74+

From README.md (lines 1–27):
> The Language Server Protocol provides IDE-like intelligence to Claude Code... exposes them to Claude in two ways:
> - **LSP Tool**: A builtin tool with 9 operations mapping directly to LSP commands [lists read-only ops]
> - **Automatic Diagnostics**: Real-time error and warning detection

**Maintainer position**: Repo is exclusively read-only LSP exposure. No mention of future write support, capability extensibility, or refactoring workflows. CLAUDE.md guidance is limited to binary auto-install and diagnostic logging.

---

## Concrete extension proposals

To add LSP write support to this repo **without modifying Claude Code core**, use these paths:

### Option 1: Slash commands per plugin
**What**: Add `<plugin>/.claude-plugin/commands/` directory with command.json files for each LSP write operation.

**Example structure**:
```
rust-analyzer/.claude-plugin/commands/
├── codeAction.json
├── rename.json
└── formatting.json
```

**Example** (rust-analyzer codeAction.json):
```json
{
  "name": "rust-analyzer-codeAction",
  "description": "Apply code action at cursor",
  "type": "tool",
  "invoke": {
    "function": "invoke_lsp_write",
    "args": {
      "method": "textDocument/codeAction",
      "lsp": "rust-analyzer"
    }
  }
}
```

**UX**: User types `/rust-analyzer-codeAction` or similar slash command.

**Pros**: Scoped per plugin, minimal config.  
**Cons**: Explosion of commands if every language server gets write operations.

### Option 2: Plugin-level skills
**What**: Add `<plugin>/.claude-plugin/skills/` with skill.json that wraps LSP write operations.

**Example structure**:
```
rust-analyzer/.claude-plugin/skills/
└── refactor.json
```

**Skill tool**: Could expose `refactorCode(file, lineRange, action)` that internally calls LSP `textDocument/codeAction` + `workspace/applyEdit`.

**UX**: Claude can call skill directly in tool use, e.g., `{"type": "tool_use", "name": "refactor-code", "input": {...}}`.

**Pros**: Clean abstraction, reusable across conversations.  
**Cons**: Requires implementing LSP write call-chain (codeAction → workspaceEdit → applyEdit). More testing.

### Option 3: MCP server per language
**What**: Add `.claude-plugin/mcp_servers/` with MCP server config that proxies LSP write methods.

**Example config**:
```json
{
  "mcp_servers": {
    "rust-analyzer-write": {
      "type": "local",
      "command": "node rust-analyzer-lsp-mcp-bridge.js",
      "env": { "RUST_ANALYZER_BIN": "rust-analyzer" }
    }
  }
}
```

**Bridge script**: Node.js process that:
1. Starts LSP server in-process
2. Exposes MCP endpoints: `applyCodeAction`, `performRename`, `formatDocument`
3. Maps MCP calls to LSP wire protocol

**UX**: Claude treats MCP tools as native capabilities, full JSON-RPC interop.

**Pros**: Fully general, no hardcoding per LSP.  
**Cons**: Requires MCP bridge script per plugin (or shared library). More infrastructure.

### Option 4: Hybrid: Skills + hooks
**What**: Add hooks that run post-SessionStart to inject LSP write skills via `${CLAUDE_PLUGIN_ROOT}/skills/` auto-discovery.

**How**:
1. Each plugin's `hooks/check-<name>.sh` generates `.claude-plugin/skills/<name>-refactor.json` dynamically.
2. Skills register themselves with Claude Code's plugin runtime.
3. Skills call a shared helper script that wraps LSP codeAction/rename/format.

**Pros**: Automated, data-driven, scales to 22 plugins.  
**Cons**: Requires changes to how hooks work (currently only `command` type, no skill injection).

---

## Conclusion

**Can claude-code-lsps be modified to add LSP write support without touching Claude Code core?**

**YES.** The cleanest path is **Option 2 (Skills)** combined with **Option 3 (MCP bridge)** for robustness:

1. **For quick POC**: Add `rust-analyzer/.claude-plugin/skills/refactor.json` that wraps a helper script invoking LSP `codeAction` + `applyEdit` locally. Skill implementation can use existing built-in file I/O without MCP.

2. **For production/scale to all 22 plugins**: Create a shared MCP bridge (`vendor/claude-code-lsps-boostvolt/lsp-write-bridge/`) that handles LSP wire protocol, registers as `.claude-plugin/mcp_servers/<lang>-write` in each plugin's config, and exposes MCP tools Claude can call natively.

3. **No core Claude Code changes needed**: Everything stays within plugin boundaries. The LSP tool continues exposing read-only ops; write operations use orthogonal extension slots (skills + MCP).

**Next steps**:
- Prototype skill-based codeAction invocation in rust-analyzer plugin (1–2 files added)
- Generalize to MCP bridge if needed for all 22 languages
- Update CLAUDE.md to document new write capability pattern

---

**Audit performed**: 2026-04-24
**Repo state**: 22 plugins, 2,381 LoC, zero write-capable code
**Risk**: None—repo is read-only LSP-only; no destructive code paths exist
