# Claude Code Plugin Install — GitHub Install Mechanics

**Researcher**: Agent B (install mechanics)
**Date**: 2026-04-28

## TL;DR

- `marketplace.json` must live at `.claude-plugin/marketplace.json` (repo root), **not** at `marketplace.json` directly — the o2-scalpel repo currently has it at the wrong path, which will cause `File not found: .claude-plugin/marketplace.json` on every `/plugin marketplace add`.
- The two-step install flow is: (1) `/plugin marketplace add o2alexanderfedin/o2-scalpel` to register the catalog, then (2) `/plugin install o2-scalpel-rust@o2-scalpel` to copy the plugin to `~/.claude/plugins/cache/`.
- The `hooks/verify-scalpel-rust.sh` script is **not** wired as a Claude Code hook — it is a freestanding shell script with no `hooks/hooks.json` counterpart; it will silently never run unless a `hooks.json` is added that binds it to `SessionStart`.

---

## 1. Install CLI

The Claude Code plugin system uses in-session slash commands (not `claude plugin …` from the shell, though the CLI form also works):

```sh
# Step 1 — register the catalog (no plugins installed yet)
/plugin marketplace add o2alexanderfedin/o2-scalpel

# Step 2 — install the Rust plugin from that catalog (user scope by default)
/plugin install o2-scalpel-rust@o2-scalpel

# Activate without restarting
/reload-plugins
```

Equivalent non-interactive (shell) form verified from docs:

```sh
claude plugin marketplace add o2alexanderfedin/o2-scalpel
claude plugin install o2-scalpel-rust@o2-scalpel --scope user   # user | project | local
```

To pin to a specific tag or branch when adding the marketplace:

```sh
/plugin marketplace add o2alexanderfedin/o2-scalpel#v1.2.0
```

The `@marketplace-name` suffix in the install command is the `name` field from `marketplace.json` (`"o2-scalpel"`), not the GitHub repo name.

---

## 2. marketplace.json — what install consumes

### Required file path

The docs are unambiguous:

> "Create `.claude-plugin/marketplace.json` in your repository root."
> Error table: `File not found: .claude-plugin/marketplace.json`

The canonical location is **`<repo-root>/.claude-plugin/marketplace.json`**.

### Current o2-scalpel state — MISMATCH

The file currently lives at `<repo-root>/marketplace.json` (no `.claude-plugin/` parent).
The repo has no `.claude-plugin/` directory at its root.

This means `/plugin marketplace add o2alexanderfedin/o2-scalpel` will fail immediately with:

```
File not found: .claude-plugin/marketplace.json
```

**Fix required**: move/rename so the file lives at `.claude-plugin/marketplace.json`.

### marketplace.json shape (what the o2-scalpel file contains)

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "o2-scalpel",           // marketplace id used in install commands
  "owner": { "name": "AI Hive(R)", "email": null, "url": null },
  "metadata": {                   // non-standard — docs say description/version go top-level or under metadata for compat
    "description": "...",
    "homepage": "...",
    "license": "MIT",
    "repository": "https://github.com/o2services/o2-scalpel",
    "version": "1.0.0"
  },
  "plugins": [
    {
      "name": "o2-scalpel-rust",
      "source": "./o2-scalpel-rust",   // relative path — resolved from marketplace root (repo root)
      "description": "...",
      "version": "1.0.0",
      "category": "development",
      "tags": ["rust", "rust-analyzer", "lsp", "refactor", "mcp", "scalpel"],
      "author": { "name": "AI Hive(R)", "email": null, "url": null }
    }
    // ... markdown, python entries omitted
  ]
}
```

The `"source": "./o2-scalpel-rust"` relative path resolves to `<repo-root>/o2-scalpel-rust/` because paths resolve relative to the marketplace root (the directory that contains `.claude-plugin/`, i.e., the repo root), not relative to the `.claude-plugin/` directory itself.

Relative-path sources **only work when the marketplace is added via git** (GitHub shorthand, git URL). Direct URL installs (`/plugin marketplace add https://…/marketplace.json`) cannot resolve relative paths — Claude Code only downloads the JSON file, not adjacent directories.

### Per-plugin source resolution

When `o2-scalpel-rust` is installed, Claude Code performs a sparse/partial clone of `o2alexanderfedin/o2-scalpel` and copies the `o2-scalpel-rust/` subdirectory into the local plugin cache. This is equivalent to a `git-subdir` fetch. The entire parent repo is not cloned in full (bandwidth optimization for monorepos).

---

## 3. Step-by-step install scenario for o2-scalpel-rust

Preconditions: Claude Code >= 1.0.0 installed and authenticated.

1. **User adds marketplace catalog**

   ```
   /plugin marketplace add o2alexanderfedin/o2-scalpel
   ```

   Claude Code clones `https://github.com/o2alexanderfedin/o2-scalpel.git`, reads `.claude-plugin/marketplace.json`, registers the catalog as `o2-scalpel` in `~/.claude/plugins/known_marketplaces.json`. No plugin files are copied yet.

2. **User browses available plugins** (optional)

   ```
   /plugin
   ```

   Opens the TUI, **Discover** tab. `o2-scalpel-rust` appears with its description and tags.

3. **User installs the plugin**

   ```
   /plugin install o2-scalpel-rust@o2-scalpel
   ```

   Claude Code resolves `source: "./o2-scalpel-rust"` relative to the repo root, performs a sparse clone of `o2alexanderfedin/o2-scalpel`, extracts the `o2-scalpel-rust/` subtree, and copies it to:

   ```
   ~/.claude/plugins/cache/o2-scalpel/o2-scalpel-rust/<version>/
   ```

   The version key is the `version` string from `plugin.json` (`"1.0.0"`) since `version` is set explicitly.

   Plugin registration is recorded in `~/.claude/settings.json` under the `user` scope (default):

   ```json
   {
     "enabledPlugins": {
       "o2-scalpel-rust@o2-scalpel": true
     }
   }
   ```

4. **Activate without restarting**

   ```
   /reload-plugins
   ```

   Claude Code loads:
   - Skills: `using-scalpel-rename-symbol-rust` and `using-scalpel-split-file-rust` from `skills/*.md` — automatically discovered and namespaced as `o2-scalpel-rust:using-scalpel-rename-symbol-rust`, etc.
   - Hooks: none (no `hooks/hooks.json` exists — see §5)
   - MCP/LSP servers: none (no `.mcp.json` or `.lsp.json` present)

5. **User verifies rust-analyzer is available**

   The plugin does not auto-check for the binary. The user must run:

   ```sh
   rustup component add rust-analyzer
   # or: cargo binstall rust-analyzer
   ```

6. **User can now invoke scalpel skills**

   Skills are auto-activated — Claude picks them up from context. Manual invocation:

   ```
   /o2-scalpel-rust:using-scalpel-rename-symbol-rust
   ```

   The skills in `skills/*.md` use `type: skill` frontmatter (not `SKILL.md` subdirectory format), which is the `commands/` flat-file variant. They are discovered correctly since the skill files use the legacy flat `.md` format.

---

## 4. Failure modes

| # | Symptom | Root cause | User-fixable? |
|---|---------|------------|---------------|
| F1 | `File not found: .claude-plugin/marketplace.json` | `marketplace.json` is at repo root, not under `.claude-plugin/` — **current state of o2-scalpel** | Repo owner must move the file; user cannot fix |
| F2 | `Plugin not found in any marketplace` | Marketplace catalog is stale or was never added | `/plugin marketplace update o2-scalpel` or re-add |
| F3 | `Executable not found in $PATH: rust-analyzer` | `rust-analyzer` not installed | `rustup component add rust-analyzer` |
| F4 | Hook `verify-scalpel-rust.sh` never runs | No `hooks/hooks.json` wires the script to `SessionStart` | Repo owner must add `hooks.json` |
| F5 | Skills appear with wrong namespace or not at all | Skills are flat `.md` files (commands format), not `<name>/SKILL.md` directories; older Claude Code may not discover them | `/plugin` Errors tab; update Claude Code |
| F6 | Plugin cache stale after a republish at the same `version` | `version: "1.0.0"` is pinned — Claude Code only updates when the version string changes | `/plugin uninstall` + reinstall, or bump version in `plugin.json` |
| F7 | `../` path traversal blocked | Plugin cannot reference files outside its directory (e.g., shared vendor/ code) | Repo owner must use symlinks within the plugin directory |
| F8 | Submodules not cloned | `vendor/serena` submodule is NOT fetched during plugin install — install only copies `o2-scalpel-rust/`, which has no submodule pointer | Submodule content must be inlined or referenced via a separate plugin; users cannot fix |
| F9 | GitHub auth failure for private repo | Repo is private and no git credential helper or `GITHUB_TOKEN` set | `gh auth login` or `export GITHUB_TOKEN=…` |
| F10 | Plugin name collision | Another marketplace also has a plugin named `o2-scalpel-rust` | Qualify install with `@o2-scalpel` suffix |
| F11 | Claude Code version too old — no `/plugin` command | Claude Code < 1.0.0 | `brew upgrade claude-code` or `npm update -g @anthropic-ai/claude-code` |
| F12 | `marketplace.json` `$schema` URL not recognized | The `$schema` field points to `anthropic.com` not `anthropic.com/claude-code/marketplace.schema.json` format; docs say Claude Code ignores this field at load time | Cosmetic only — no functional impact |

---

## 5. Hook lifecycle

### Current state of o2-scalpel-rust

The plugin has:

```
o2-scalpel-rust/
  hooks/
    verify-scalpel-rust.sh    # shell script
```

There is **no `hooks/hooks.json`**. Without `hooks.json`, Claude Code does not know `verify-scalpel-rust.sh` exists and will never execute it.

### How hooks work in plugins (per docs)

Plugin hooks are declared in `hooks/hooks.json` at the plugin root. The format mirrors the user-level hooks config:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/verify-scalpel-rust.sh"
          }
        ]
      }
    ]
  }
}
```

`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's cache directory at runtime (changes across versions).

### `SessionStart` semantics

- Fires when a Claude Code session begins or resumes.
- Hook receives a JSON blob on stdin with `session_id`, `cwd`, `permission_mode`, etc.
- Exit code 0 = success (allow session to continue).
- Exit code 2 = blocking error: session startup is blocked and stderr is shown to the user.
- Any other non-zero = non-blocking warning shown to user.

The `verify-scalpel-rust.sh` script uses `exit 1` on failure (not exit 2), so it would produce a non-blocking warning rather than a hard block. To make a missing `rust-analyzer` block the session, it should exit with code 2.

---

## 6. Skill activation

### Current skill format

The skills under `o2-scalpel-rust/skills/` are **flat `.md` files** (the `commands/` legacy format), not the newer `<name>/SKILL.md` subdirectory format:

```
skills/
  using-scalpel-rename-symbol-rust.md
  using-scalpel-split-file-rust.md
```

The frontmatter uses `type: skill` and `name:` fields — this is the older flat-command format. Per docs, both formats are supported, but `skills/<name>/SKILL.md` is preferred for new plugins.

### Discovery and activation

- Skills are **automatically discovered** when the plugin is installed.
- No user opt-in is needed beyond installing the plugin.
- After `/reload-plugins`, skills appear in `/help` under the plugin namespace.
- Skill names are namespaced: `o2-scalpel-rust:<skill-name>`.
- Claude invokes skills automatically based on task context when the `description` frontmatter matches user intent.

### Skill invocation examples

```
/o2-scalpel-rust:using-scalpel-rename-symbol-rust
/o2-scalpel-rust:using-scalpel-split-file-rust
```

The `description` fields in the skill frontmatter (`"When user asks to rename a symbol across the workspace in Rust…"`) guide Claude's automatic selection.

---

## 7. What the user must do after install to actually use o2-scalpel-rust

1. Ensure `rust-analyzer` is on `$PATH`: `rustup component add rust-analyzer`
2. Open a Rust project (a directory with `Cargo.toml`).
3. Ask Claude to rename a symbol, split a file, etc. — skills fire automatically via description matching.
4. The MCP server (Serena/o2-scalpel-engine) must also be configured. The plugin does not include a `.mcp.json` — this is a gap: Claude gets the skills but no MCP tool backing them unless the MCP server is separately running and wired.

---

## Citations

- Discover and install plugins: https://code.claude.com/docs/en/discover-plugins
- Create plugins: https://code.claude.com/docs/en/plugins
- Plugin marketplaces (create/distribute): https://code.claude.com/docs/en/plugin-marketplaces
- Plugins reference (schemas, cache paths, env vars): https://code.claude.com/docs/en/plugins-reference
- Hooks reference: https://code.claude.com/docs/en/hooks

---

## Open questions for the synthesis pair

1. **marketplace.json path**: The repo has `marketplace.json` at root, but docs require `.claude-plugin/marketplace.json`. Is the current path intentional (relying on a Claude Code extension/compatibility shim), or is this a latent bug that blocks all installs from GitHub?

2. **Missing hooks.json**: `verify-scalpel-rust.sh` will never run without a `hooks/hooks.json`. Is the intent to add `hooks.json`, or is the script vestigial/test-only?

3. **Missing .mcp.json**: The plugin ships skills that call MCP tools (`scalpel_rename_symbol`, `scalpel_split_file`), but no `.mcp.json` wires the MCP server into the plugin. Users who install only this plugin from GitHub will have the skills but no backing tools. Is the MCP server expected to be pre-configured separately, or should the plugin bundle a `.mcp.json`?

4. **Skill format migration**: Skills use flat `.md` format (legacy `commands/`). The docs recommend the `skills/<name>/SKILL.md` subdirectory format for new plugins. Should skills be migrated before E2E tests are written, or should tests accept the current format?

5. **Correct GitHub repo URL**: `marketplace.json` lists `"repository": "https://github.com/o2services/o2-scalpel"` but the actual remote is `https://github.com/o2alexanderfedin/o2-scalpel.git`. The install command must use `o2alexanderfedin/o2-scalpel` (the actual owner), not `o2services/o2-scalpel`. E2E tests should use the verified URL.

6. **Submodule gap**: The MCP server lives in `vendor/serena` (a git submodule). Plugin install does NOT clone submodules. Any E2E test that exercises live MCP tool calls needs the submodule pre-initialized in the test environment separately.
