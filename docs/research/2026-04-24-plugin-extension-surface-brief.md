# Claude Code Plugin Extension-Surface Research — LSP Write/Refactor Feasibility

**Specialist C.** Scope: can plugin slots, individually or combined, deliver LSP write/refactor capability without modifying Claude Code core?

**Bottom line up front.** Yes, it is buildable today — but the only path with real leverage is **a plugin-bundled MCP server (`mcp_servers` / `.mcp.json`) that runs its own LSP client** and exposes `rename`, `codeAction`, and `applyEdit` as MCP tools. Every other slot (`.lsp.json`, hooks, slash commands, skills, subagents) is either read-only, prompt-only, or too indirect to carry a stateful LSP session. The MCP path is modest work; its biggest cost is the two-LSP-process problem for heavy servers like rust-analyzer.

---

## 1. Slot-by-slot audit

### 1.1 `.lsp.json` — canonical schema (read-only)

Location: `<plugin-root>/.lsp.json` or inline `lspServers` in `plugin.json` ([plugins-reference §LSP](https://code.claude.com/docs/en/plugins-reference#lsp-servers)).

Schema: required `command` + `extensionToLanguage`; optional `args`, `transport` (stdio\|socket), `env`, `initializationOptions`, `settings`, `workspaceFolder`, `startupTimeout`, `shutdownTimeout`, `restartOnCrash`, `maxRestarts`.

**What it drives**: CC's built-in `LSP` umbrella tool exposes **exactly 9 read-only ops** — `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls` — plus `publishDiagnostics` (canonical plugin README).

**Write verdict: zero.** No `rename`/`codeAction`/`applyEdit`. `initializationOptions` tunes the server but the CC-side tool surface is fixed.

### 1.2 `mcp_servers` / `.mcp.json` — full control, auto-started

Location: `<plugin-root>/.mcp.json` or inline `mcpServers` in `plugin.json` ([plugins-reference §MCP servers](https://code.claude.com/docs/en/plugins-reference#mcp-servers)). Standard MCP stdio/HTTP config. Supports `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${user_config.*}`, `${ENV_VAR}` substitution.

Minimal example:

```json
{
  "mcpServers": {
    "rust-write": {
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/lsp-write-bridge",
      "args": ["--lsp", "rust-analyzer", "--workspace", "${CWD}"],
      "env": { "RA_LOG": "error" }
    }
  }
}
```

**Integration behavior (verbatim from docs)**: servers start automatically when the plugin is enabled, appear as standard MCP tools, tools are namespaced `mcp__<server>__<tool>` (e.g. `mcp__rust-write__rename`). Tool-search is deferred-loading by default — only names appear at session start, schemas load on demand. MCP servers are the **only** plugin slot where tool-call outputs go through `PostToolUse` with `updatedMCPToolOutput` (hooks doc), meaning you can post-process and hand back edits Claude applies via normal Edit/Write.

**Write verdict: full.** The MCP server owns its own LSP connection, applies `textDocument/rename`, `textDocument/codeAction/resolve`, `workspace/applyEdit`, and returns a `WorkspaceEdit` translated to plain text diffs — or directly writes files if permissions allow.

### 1.3 Slash commands / Skills

"**Custom commands have been merged into skills**" ([skills doc](https://code.claude.com/docs/en/skills)). Same `/name` invocation. Frontmatter: `name`, `description`, `arguments`, `allowed-tools`, `disable-model-invocation`, `user-invocable`, `context: fork`, `agent`, `paths`, plus others.

Body is a **prompt template**. Inline ` !`cmd` ` and ```` ```! ```` blocks run before the model sees the prompt; their stdout is inlined. So a skill **can** shell out to an LSP helper and hand Claude a diff — but the edit still goes through the Edit tool with the model in the loop. No tool-calling from skill bodies.

**Write verdict: indirect.** Fine for `/lsp-rename foo.rs 42 10 bar` one-shots; awkward for iterative refactors.

### 1.4 Subagents (`agents/*.md`)

Frontmatter: `name`, `description`, `tools` (allowlist), `disallowedTools`, `model`, `skills`, `isolation: worktree`, `maxTurns`. **Critical plugin restriction:** "plugin subagents do not support the `hooks`, `mcpServers`, or `permissionMode` fields" ([plugins-reference §Agents](https://code.claude.com/docs/en/plugins-reference#agents)). A plugin subagent cannot scope a bespoke MCP server to itself — it sees the session-wide pool. `tools` allowlist *can* contain `mcp__rust-write__rename` etc.

**Write verdict: orchestrator only.** Good as a wrapper over the MCP write tools (prepare→rename→verify→commit), not a primary surface.

### 1.5 Hooks — fine-grained decorator

29 event types ([hooks doc](https://code.claude.com/docs/en/hooks)). Relevant write slots:

| Event          | Block | Modify input | Inject context | Modify output         |
| -------------- | ----- | ------------ | -------------- | --------------------- |
| `PreToolUse`   | Yes   | **Yes** (`updatedInput`) | Yes | — |
| `PostToolUse`  | Yes   | — | Yes | **MCP only** (`updatedMCPToolOutput`) |
| `SessionStart` | No    | — | Yes | — |

Protocol: JSON on stdin → JSON on stdout (exit 0). A `PreToolUse` on `Edit` can shell out, transform the edit via LSP (e.g. fix renames cross-file), return `updatedInput` with corrected `new_string`. A `PostToolUse` on `Edit` can run diagnostics and block with `decision: block` + `reason`.

**Write verdict: decorator, not driver.** Hooks fire on existing tool calls — they can't *originate* a refactor. Pair with P1.

### 1.6 Monitors (adjunct)

`monitors/monitors.json` (CC v2.1.105+) streams a shell command's stdout as notifications. Useful for pushing LSP diagnostics into context; not a write path.

---

## 2. Architecture options

### (P1) MCP server bundled in plugin — **RECOMMENDED**

Sketch: `rust-analyzer-write` plugin ships `.mcp.json` pointing at a small Go/Python/Rust binary. On start, the binary spawns its own rust-analyzer child, completes `initialize` with full client capabilities (`workspace.workspaceEdit.documentChanges: true`, `textDocument.rename.prepareSupport: true`, `textDocument.codeAction.resolveSupport`), and exposes MCP tools: `lsp_rename(file, line, col, new_name)`, `lsp_code_actions(file, range)`, `lsp_apply_code_action(id)`, `lsp_format(file)`, `lsp_organize_imports(file)`. Results are `WorkspaceEdit` objects; the bridge either applies them directly or returns a unified diff the model feeds to Edit.

- **Latency**: dominated by cold rust-analyzer indexing on first call (same as CC's own). Subsequent calls: milliseconds.
- **Accuracy**: full LSP fidelity — server-side cross-file rename, trait-aware code actions.
- **Complexity**: medium. Reference implementations exist ([tombi-toml/lsp-mcp](https://github.com/tombi-toml), [multilspy](https://github.com/microsoft/multilspy), [cclsp write fork experiments](https://github.com/Piebald-AI/claude-code-lsps/issues)).
- **Multi-language**: clean — one plugin per language server, each namespaced `mcp__rust-write__*`, `mcp__gopls-write__*`. No collision because MCP namespaces by server name (doc: "Server and prompt names are normalized (spaces become underscores)").
- **Overdesign?** No — it's the one place CC opened for exactly this.

### (P2) Slash command + shell helper

Sketch: `/lsp-rename file line col new-name` invokes a short-lived helper that opens rust-analyzer, does one rename, dumps a diff, exits. Skill body shows the diff and instructs Claude to apply via Edit.

- **Latency**: bad. Every call pays rust-analyzer's cold indexing (30s–2min for large crates). No warm cache.
- **Accuracy**: same as P1 if helper is correct.
- **Complexity**: low. No daemon.
- **Scaling**: one skill per refactor op × per language.
- **Overdesign?** No, but the cold-start cost makes it unusable for interactive refactors. Acceptable for one-off "/lsp-format" style tools.

### (P3) Long-lived sidecar daemon + SessionStart hook + Unix socket

P1 already achieves a long-lived session server — MCP servers run for the session. P3 is P1 re-invented with extra pipes and lifecycle management. **Overdesign. Skip.**

### (P4) IPC into CC's existing LSP process

CC owns stdio on the rust-analyzer child. No public IPC. **Infeasible without CC core changes.**

### (P5) Pure-prompt skill/agent

No LSP: Grep + Edit only. Works today, but fails the brief — loses semantic disambiguation (trait dispatch, shadowed names, macros).

---

## 3. Cross-cutting concerns

### Two-LSP-process problem

rust-analyzer FAQ: two instances contend on `target/` cargo lock. Documented mitigation: separate target dir (`rust-analyzer.cargo.targetDir`). Pass this in the bridge's `initializationOptions`. clangd (compile-commands + in-memory index), gopls, pyright: coexist fine. **Practical fix**: rust-analyzer-only, force `${CLAUDE_PLUGIN_DATA}/ra-target` on the write-bridge child.

### Capability negotiation

For full assist set during `initialize` advertise: `workspace.applyEdit`, `workspace.workspaceEdit.{documentChanges,resourceOperations:["create","rename","delete"],failureHandling:"textOnlyTransactional"}`, `textDocument.rename.prepareSupport`, `textDocument.codeAction.{codeActionLiteralSupport,resolveSupport.properties:["edit"],dataSupport}`, `textDocument.{formatting,rangeFormatting,inlayHint}`.

### Discovery of sibling `.lsp.json`

No registry handle, but filesystem access isn't gated — `~/.claude/plugins/cache/*/*/.lsp.json` is readable. Simpler: **one write-companion per language** mirroring the read plugin's config with its own target-dir.

### Tool-name collision

MCP namespaces by server name: `mcp__rust-write__rename`, `mcp__clangd-write__rename`. No collision.

---

## 4. Recommendation

**Ranked**:
1. **P1 (plugin MCP server)** — the designed path. Adopt this.
2. P1 + hooks (PostToolUse runs diagnostics after Edit, feeds errors back) — optional polish.
3. P2 for non-interactive one-shot tools only.
4. Ignore P3, P4, P5 for this goal.

### File layout for the recommended write-companion plugin

```
rust-analyzer-write/
├── .claude-plugin/
│   └── plugin.json              # name: rust-analyzer-write, deps: rust-analyzer
├── .mcp.json                    # mcpServers.rust-write -> ${CLAUDE_PLUGIN_ROOT}/bin/bridge
├── bin/
│   └── bridge                   # compiled helper (Rust/Go), stdio MCP + stdio LSP client
├── hooks/
│   ├── hooks.json               # SessionStart: ensure bridge deps; PostToolUse(Edit): re-diagnose
│   └── post-edit-diagnose.sh
├── skills/
│   └── rust-refactor/
│       └── SKILL.md             # optional playbook: "prefer mcp__rust-write__rename over text edits"
└── agents/
    └── rust-refactorer.md       # subagent with tools: mcp__rust-write__*, Edit, Read
```

Tools exposed by the bridge (MCP schema):
- `rename(uri, position, newName) -> WorkspaceEdit|applied`
- `code_actions(uri, range, only?) -> CodeAction[]`
- `resolve_and_apply_code_action(action) -> applied`
- `format(uri, range?) -> applied`
- `organize_imports(uri) -> applied`
- `extract_function(uri, range, name) -> applied` (rust-analyzer assist)
- `diagnostics(uri) -> Diagnostic[]`

### Effort sizing (no time estimates, per project CLAUDE.md)

| Component | Size | Notes |
| --- | --- | --- |
| MCP↔LSP bridge core (rename, code_actions, format) | **medium** | Rust: `tower-lsp` client + `rmcp` server; ~800–1500 LoC |
| Plugin manifest + .mcp.json + hooks | **small** | Copy from `boostvolt/claude-code-lsps` + add .mcp.json |
| rust-analyzer target-dir override + warm-up on SessionStart | **small** | init option |
| PostToolUse auto-diagnose hook | **small** | shell script invoking `bridge diagnose` |
| Per-additional-language plugin (clangd-write, gopls-write, pyright-write) | **small** each | reuse bridge, swap server command |
| Skill playbook + refactor subagent | **small** | optional but improves auto-invocation |

### Worth building vs. waiting?

**Build a narrow v0.1**: `rename`, `format`, `organize_imports`, `quickfix code_actions` for rust + ts (vtsls). These are the ops where LSP fidelity decisively beats grep+Edit. The long tail (extract-function, inline-variable, move-item) is lower ROI and where Anthropic will likely land first. The architecture isn't overdesign — it's exactly what `mcp_servers` was opened for, filesystem-local, and degrades gracefully (missing binary → inert plugin, read LSP unaffected).

**Risk**: if Anthropic ships `LSP.rename` natively, v0.1 becomes redundant. Mitigation: keep v0.1 scope tight — the same floor where the semantic win over Edit is largest.

---

## Citations

- Plugin reference: https://code.claude.com/docs/en/plugins-reference
- Hooks reference: https://code.claude.com/docs/en/hooks
- MCP in Claude Code: https://code.claude.com/docs/en/mcp
- Skills: https://code.claude.com/docs/en/skills
- Sub-agents: https://code.claude.com/docs/en/sub-agents
- Canonical `.lsp.json` schema: `/Users/alexanderfedin/.claude/plugins/marketplaces/claude-code-lsps/README.md:405-445`
- Reference plugin (rust-analyzer): `/Users/alexanderfedin/.claude/plugins/marketplaces/claude-code-lsps/rust-analyzer/{.lsp.json,.claude-plugin/plugin.json,hooks/hooks.json}`
- Marketplace manifest: `/Users/alexanderfedin/.claude/plugins/marketplaces/claude-code-lsps/.claude-plugin/marketplace.json`
- Built-in `LSP` tool operations: `/Users/alexanderfedin/.claude/plugins/marketplaces/claude-code-lsps/README.md:14-27`
- rust-analyzer target-dir guidance: https://rust-analyzer.github.io/book/faq.html
