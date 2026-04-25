# Plugin Marketplace Decision Research

## Official Conventions (Cited from Docs)

**Plugin Discovery & Installation:**
- Users discover plugins via `/plugin` command or Claude Code's built-in Discover tab
- Installation syntax: `/plugin install {plugin-name}@{marketplace-repo}` or from official marketplace
- Marketplace repos use `.claude-plugin/marketplace.json` to list plugins (see [Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces))

**Single-Plugin vs. Multi-Plugin Marketplaces:**
- Single-plugin repos work but **discoverability is poor**—one-off repos don't appear in plugin directories
- Multi-plugin marketplaces are the conventional pattern: they host 10–40+ plugins in parallel (see [Plugins reference](https://code.claude.com/docs/en/plugins-reference))
- Marketplace repos require a `marketplace.json` file at `.claude-plugin/marketplace.json` listing all plugins and their git refs

**Plugin Manifest:**
- Required: `name`, `description`, `version` (optional but recommended for explicit versioning vs. commit SHA)
- Optional: `author`, `homepage`, `repository`, `license`
- Namespaced skills: `/plugin-name:skill-name` (prevents conflicts)
- Plugins can include: skills, agents, hooks, **MCP servers (`.mcp.json`)**, LSP servers (`.lsp.json`), monitors

**MCP-Server-Bearing Plugins:**
- Officially supported—plugins can bundle `.mcp.json` alongside skills/agents (see [MCP integration](https://code.claude.com/docs/en/mcp))
- Example: GitHub MCP server plugin is distributed via the official marketplace
- No special publishing requirements beyond standard plugin structure

---

## Marketplace Inventory

| Marketplace | Type | Plugin Count | Focus | Contribution Model |
|---|---|---|---|---|
| **anthropics/claude-plugins-official** | Official | ~50–100 | Skills, agents, LSP, MCP | Curated; submission form |
| **boostvolt/claude-code-lsps** | Community | 22 LSP plugins | Language servers only | PRs welcome; MIT |
| **Piebald-AI/claude-code-lsps** | Community | 40+ LSP plugins | Language servers only | Auto-validated; generated from `.lsp.json` |
| **jeremylongshore/claude-code-plugins-plus-skills** | Mega | 423 plugins, 2,849 skills | Multi-purpose aggregate | Published daily via GitHub Actions |
| **ComposioHQ/awesome-claude-plugins** | Curated list | ~50+ | Production-ready plugins | Reference directory (not a marketplace repo) |
| **claudemarketplaces.com** | Directory | 110k visitors/mo | Plugin search engine | Third-party aggregator |

**Key pattern:** Successful community marketplaces either:
1. **Specialize** (boostvolt/Piebald: LSP only)
2. **Aggregate** (jeremylongshore: all plugin types, auto-generated)
3. **Curate** (Anthropic official: quality-gated)

---

## Single-Plugin vs. Multi-Plugin Trade-Off Matrix

| Dimension | Single-Plugin Repo | Multi-Plugin Marketplace |
|---|---|---|
| **Discoverability** | Poor—not listed in plugin directories | Good—users can browse one repo for multiple plugins |
| **Installation** | `/plugin install o2-scalpel@o2alexanderfedin/o2-scalpel-plugin` | `/plugin install o2-scalpel@o2alexanderfedin/claude-code-plugins` |
| **Versioning** | Independent; can bump at own cadence | Coupled to marketplace repo; users see `marketplace.json` snapshot |
| **Contributor friction** | None; direct repo access | Must contribute via PR into shared marketplace |
| **Maintenance burden** | Minimal; just one plugin | Higher; maintain marketplace metadata & test suite |
| **Market signal** | Weak—solo repo doesn't attract users | Strong—multi-plugin repos become discovery hubs |
| **Future consolidation** | Hard to migrate to marketplace later (breaking URLs) | Easy to add more plugins; URL stability maintained |

**Finding:** Single-plugin repos are viable for niche, well-marketed tools but **marketplace repos are the industry standard** for distribution. Migrating later is painful because users have hardcoded the original URL.

---

## MCP-Server-Bearing Plugin Survey

**o2-scalpel's situation:**
- Bundles MCP server (`o2-scalpel-mcp`) with plugin skills/agents
- This is officially supported; several examples exist in the wild

**Patterns found:**
1. **GitHub MCP server plugin** (official marketplace): Uses `.mcp.json` in plugin root; users enable plugin once, MCP auto-configures
2. **Custom MCP marketplace plugins** (ComposioHQ, ziiliz): MCP servers exposed as plugin + skills; one install handles both
3. **LSP-only plugins** (boostvolt/Piebald): Only `.lsp.json`; pure code-intelligence focus, no MCP

**Implication for o2-scalpel:**
- No special handling needed—structure as standard plugin with `.mcp.json` + skills
- If you publish to a marketplace, MCP auto-configures when plugin is enabled
- If you publish standalone, MCP only activates for users who explicitly install that repo

---

## Future-Proofing: Anthropic Native LSP Write Tool (#24249)

**Scenario:** Anthropic ships built-in LSP write support (bypassing o2-scalpel's LSP plugin).

**Impact analysis:**

| Publishing Choice | Risk | Mitigation |
|---|---|---|
| Standalone repo | **High**—dead code, broken installation URL | Deprecation notice; migrate to marketplace repo later (painful) |
| Multi-plugin marketplace | **Medium**—o2-scalpel becomes optional; users have alternative | Clear docs: "Use o2-scalpel for custom languages; use Anthropic native for standard LSPs" |
| PR into boostvolt/Piebald | **Low**—upstream maintainers handle deprecation; you maintain gracefully | Upstream deprecates alongside Anthropic; users get `v1.0-deprecated` tag |

**Best posture:**
- Publish to own marketplace **now** (o2alexanderfedin/claude-code-plugins)
- If Anthropic ships native: fork boostvolt/Piebald, add o2-scalpel, then deprecate your marketplace
- Marketplace approach lets you control the deprecation narrative independently

---

## Recommendation

**Primary: Multi-Plugin Marketplace (Option a, refined)**

- **Repo:** `o2alexanderfedin/claude-code-plugins` (not `o2-scalpel-plugin`)
- **Rationale:**
  - Marketplace repos are the industry standard (all successful community distributions use this)
  - Bundles MCP + LSP + skills in one install: cleaner UX than standalone
  - Future-proofs against consolidation (can add more plugins later without breaking URLs)
  - Marketplace URL is stable; single-plugin repos get migrated away
  - Aligns with boostvolt/Piebald patterns; easier to contribute upstream later

- **Structure:**
  ```
  o2alexanderfedin/claude-code-plugins/
  ├── .claude-plugin/
  │   └── marketplace.json          # lists o2-scalpel, future plugins
  ├── o2-scalpel/
  │   ├── .claude-plugin/plugin.json
  │   ├── .mcp.json                 # MCP server config
  │   ├── skills/                   # LSP write, refactor, etc.
  │   └── README.md
  └── [future plugins...]
  ```

- **Installation:** `/plugin marketplace add o2alexanderfedin/claude-code-plugins`  
  Then: `/plugin install o2-scalpel@o2alexanderfedin/claude-code-plugins`

**Alternative: PR into boostvolt/claude-code-lsps (Option b)**

- Trade-off: No MCP bundling (LSP-only plugins)
- Risk: boostvolt may not accept MCP plugins; fork would be needed
- Benefit: existing user base (~1K+ users) discover your plugin in popular marketplace

**Fallback: Single-Plugin Repo (Option c)**

- Only if: you want total independence, expect rapid iteration
- Drawback: manually market to reach users; poor discoverability
- Plan migration path to marketplace within 6 months

**Migration Path if Anthropic Ships Native LSP Write:**

1. Fork boostvolt → o2alexanderfedin/claude-code-lsps-community
2. Add o2-scalpel as optional plugin (defers to Anthropic native if available)
3. Tag your marketplace v1.0 as "maintained community fork"
4. Deprecate standalone marketplace; users auto-migrate via upstream PR

---

## Sources

- [Create plugins - Claude Code Docs](https://code.claude.com/docs/en/plugins)
- [Plugins reference - Claude Code Docs](https://code.claude.com/docs/en/plugins-reference)
- [Create and distribute a plugin marketplace - Claude Code Docs](https://code.claude.com/docs/en/plugin-marketplaces)
- [Discover and install plugins - Claude Code Docs](https://code.claude.com/docs/en/discover-plugins)
- [anthropics/claude-plugins-official - GitHub](https://github.com/anthropics/claude-plugins-official)
- [boostvolt/claude-code-lsps - GitHub](https://github.com/boostvolt/claude-code-lsps)
- [Piebald-AI/claude-code-lsps - GitHub](https://github.com/Piebald-AI/claude-code-lsps)
- [Connect Claude Code to tools via MCP - Claude Code Docs](https://code.claude.com/docs/en/mcp)
- [ComposioHQ/awesome-claude-plugins - GitHub](https://github.com/ComposioHQ/awesome-claude-plugins)
