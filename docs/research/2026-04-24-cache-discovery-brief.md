# Plugin Discovery + Lazy Spawn — Resolution Research

**Specialist A1** — for o2.scalpel MCP server.

Verified locally: `~/.claude/plugins/cache/claude-code-lsps/<server>/<version>/.lsp.json` exists today and uses a stable, trivially-parseable shape (e.g. `rust-analyzer/1.0.0/.lsp.json` → `{"rust": {"command": "rust-analyzer", "extensionToLanguage": {".rs": "rust"}}}`). `~/.claude/plugins/installed_plugins.json` is a sibling manifest with versioned install paths. So the *target shape* is already aligned with mature ecosystems — the question is "do we hand-roll the walker or borrow one?"

---

## Q1 — Plugin / extension discovery survey

| Ecosystem | Discovery mechanism | Stability guarantee | Plugin-author failure mode |
|---|---|---|---|
| **VS Code** | `vscode.extensions.all` + `getExtension(id)` + `onDidChange` event; declarative `extensionDependencies` in `package.json` | Documented stable API; host owns the path | Use `extensionDependencies` for hard deps; `getExtension()` + null-check for soft deps |
| **Neovim** | `runtimepath` scan; `vim.api.nvim_list_runtime_paths()`; lazy.nvim resolves via Git URL | `runtimepath` is the documented contract | Plugin missing → graceful no-op |
| **Emacs `package.el`** | `package-alist` after `package-initialize`; `load-path` scan | `package-alist` is the documented index | `(require 'foo nil 'noerror)` |
| **Sublime Text** | `sublime.find_resources("*.sublime-settings")` walks all installed packages via host API | API-mediated, never raw FS | Returns `[]` on miss |
| **Atom/Pulsar** | `atom.packages.getActivePackages()` / `getLoadedPackages()` | Stable host API | Null-check |
| **Python** | `importlib.metadata.entry_points(group=...)` — packages declare exposed groups in their own metadata | PEP 621 / PEP 660; standard-library since 3.10 | `EntryPoint.load()` raises → catch + continue |
| **NodeJS** | `require.resolve()` + `peerDependencies`; npm guarantees flat-or-nested `node_modules` resolution | Resolution algorithm is specced | Missing peer → warning, not failure |
| **Bazel** | `WORKSPACE`/`MODULE.bazel` declared, queried via `bazel query` | Declarative, hermetic | Build fails loudly |
| **GIMP/Inkscape** | FS scan of `~/.config/<app>/plug-ins/` for executables + manifest | Host-documented dirs | Skip with log |

**Pattern winners:** (a) host-mediated API (VS Code, Sublime, Atom — best, but Claude Code doesn't expose one to MCP servers); (b) declarative manifest in well-known location (Emacs, Python entry-points, Neovim `runtimepath`).

**Established Python libs for "scan parent host's plugin dir":** None exist for Claude Code specifically. But the general primitives are dead-simple stdlib:
- `pathlib.Path.glob("**/.lsp.json")` — 1 line, no dep.
- `platformdirs` (PyPI, formerly `appdirs`, ~30M downloads/month) — *the* canonical way to resolve `~/.claude` cross-platform without re-implementing `XDG_CONFIG_HOME`/`%APPDATA%`/macOS conventions ([platformdirs](https://github.com/platformdirs/platformdirs)).
- `pluggy` (pytest's plugin system, Python's de-facto plugin framework) — overkill here because it expects plugins to import as Python packages, not arbitrary JSON manifests.

**Verdict on Q1:** No library wraps "walk a host's plugin cache." It's stdlib `pathlib.glob` + `json.load`. The *useful* dependency is `platformdirs` for the base path.

---

## Q2 — Lazy spawn survey

| System | Trigger | Lifetime | Idle shutdown | Failure recovery |
|---|---|---|---|---|
| **Neovim `vim.lsp.enable()`** | `FileType` autocmd → first matching buffer | Per-buffer attach; one server process shared across buffers of same root | `:LspStop`, manual; some configs add inactivity timer | `on_exit` callback; user retries with `:LspStart` |
| **VS Code language extensions** | Activation events (`onLanguage:rust`) | Process per workspace | Shutdown on workspace close | Extension host restarts crashed servers automatically |
| **Serena (multilspy)** | First tool call needing language X | Per session | Explicit `shutdown` on MCP disconnect | Producer-consumer reader thread; 2s `shutdown` request then SIGTERM ([Serena LSP integration](https://deepwiki.com/oraios/serena/5-language-server-protocol-integration)) |
| **mcp-language-server** | First semantic tool call | Per MCP-server lifetime | None — dies with parent | Restart = restart MCP server |
| **cclsp** | First tool call | Per MCP-server lifetime | None | Same |
| **MCP itself (Claude Code → MCP)** | Eager: spawned at session start ([docs](https://code.claude.com/docs/en/mcp)) | Session lifetime | Claude Code closes idle stdio pipe after threshold ([issue #1478](https://github.com/anthropics/claude-plugins-official/issues/1478)) — **does not auto-respawn** | User runs `/reload-plugins` |
| **SQLAlchemy** | Lazy: first `engine.connect()` ([docs](https://docs.sqlalchemy.org/en/20/core/pooling.html)) | Pool-managed | `pool_recycle` seconds; `pool_pre_ping` validates on checkout | Pre-ping → invalidate → reconnect transparently |
| **psycopg pool** | Lazy or eager (`open=True`) | Pool-bounded | `max_idle` | Background reconnect |
| **kubelet image pull** | First container start | Cached on node | LRU eviction | Re-pull |

**Pattern winners:** Lazy-on-first-use + pool_pre_ping-style health check + transparent reconnect (SQLAlchemy is the gold standard).

**Python libraries that already implement "lazy-spawn LSP + idle-shutdown + reconnect":**
- **`multilspy`** (Microsoft) — Python LSP client, implements stdio spawn, JSON-RPC, async query API. Does *not* idle-shutdown by default but exposes lifecycle hooks. ([repo](https://github.com/microsoft/multilspy))
- **`lsp-client`** (community, well-typed) — alternative Python LSP client. ([repo](https://github.com/lsp-client/lsp-client))
- **`pylspclient`** — minimal, less maintained.
- General subprocess pool: nothing canonical — `subprocess.Popen` + `atexit` + a dict is what everyone writes. Async: `asyncio.subprocess` + `asyncio.Lock`.

**Verdict on Q2:** `multilspy` is the obvious adopt-don't-build choice. Serena already proved the pattern in the *exact* same context (MCP server wrapping LSPs). Idle-shutdown logic on top of multilspy is ~40 lines.

---

## Q3 — Filesystem-watch on plugin cache

**Recommendation: NO watch. Snapshot at startup. Re-snapshot on a `reload` MCP tool.**

Reasoning:
1. Claude Code itself requires `/reload-plugins` after install/disable ([docs](https://code.claude.com/docs/en/mcp)). Mid-session install isn't expected to "just work" host-side either.
2. `watchdog` works ([PyPI](https://pypi.org/project/watchdog/)) but adds a thread, FSEvents/inotify complexity, and a dependency for a near-zero-value feature.
3. None of Serena, cclsp, or mcp-language-server watch their config dirs. That's the precedent.
4. Cost of being wrong is one user-visible "run /reload-plugins" — acceptable.

Expose `scalpel_reload_plugins` as an MCP tool for the rare mid-session case. Cheap, explicit, debuggable.

---

## Q4 — Mitigations for unstable host paths

Walking `~/.claude/plugins/cache/` is piggybacking on undocumented internals. Established mitigations, ranked by ROI:

1. **Env-var override** — `SCALPEL_PLUGINS_CACHE=/path` short-circuits discovery. Zero-cost insurance. Universal pattern (cf. `XDG_*`, `PIP_CONFIG_FILE`, `RUSTUP_HOME`).
2. **Explicit config file** — `~/.config/o2.scalpel/config.toml` with `[lsp_servers]` table users *can* fill manually. Decouples scalpel from the host entirely when needed.
3. **Path-resolution chain with logging** — try (a) `$SCALPEL_PLUGINS_CACHE`, (b) explicit config file, (c) `~/.claude/plugins/cache/`, (d) fail with actionable error listing all attempted paths. This is the `platformdirs`/`pip` pattern.
4. **Schema validation + version pin** — `pydantic` model for `.lsp.json`. If schema changes, fail loud with a descriptive message and a link to upstream issue tracker. Not "swallow and pray."
5. **Integration test on real host snapshot** — commit a fixture tree (`tests/fixtures/claude-cache/...`) capturing the real layout. CI catches host upgrades that break parsing.
6. **Upstream feature request** — file an Anthropic issue asking for a documented "list installed plugins" API. Low cost, possibly high payoff. cf. how rust-analyzer formalized `experimental/serverStatus`.

**What *not* to do:** don't poll the path, don't shell out to `claude plugin list`, don't reverse-engineer the SQLite/JSON internal cache format. The flat `.lsp.json` files are the public-ish surface; stay there.

---

## Recommendations for o2.scalpel

1. **Discovery mechanism:** stdlib `pathlib.Path(base).glob("*/*/.lsp.json")` + `pydantic` schema for validation. Base path resolved via `platformdirs.user_data_dir("claude")` overridable by `SCALPEL_PLUGINS_CACHE` env var, then by `~/.config/o2.scalpel/config.toml` `[discovery].plugin_cache`. ~50 lines total.
2. **Spawn lifecycle:** adopt **multilspy** as the LSP client. Lazy spawn on first tool call referencing a language. One process per (language, project_root). Idle-shutdown after 10 min inactivity (configurable). On `BrokenPipeError`/`ProcessLookupError` → log, drop from registry, transparently respawn on next call (SQLAlchemy `pool_pre_ping` analogue: `is_alive()` check on checkout).
3. **Watch behavior:** **NO.** Snapshot at startup. Expose `scalpel_reload_plugins` MCP tool for explicit re-scan. Matches Serena/cclsp/mcp-language-server precedent and Claude Code's own `/reload-plugins` UX.
4. **Cache-path mitigation:** env-var override + config file + path-chain logging + pydantic schema + fixture-based integration test + upstream feature request. The full belt-and-suspenders, because each piece is cheap individually.

---

## Are we reinventing wheels?

| Concern | Reinventing? | Established alternative |
|---|---|---|
| LSP JSON-RPC client, framing, request routing | **YES — don't** | [`multilspy`](https://github.com/microsoft/multilspy) (Microsoft, used by Serena) |
| Cross-platform user-dir resolution | **YES — don't** | [`platformdirs`](https://github.com/platformdirs/platformdirs) |
| `.lsp.json` schema parsing/validation | **YES — don't** | `pydantic` v2 |
| Walking `~/.claude/plugins/cache/` glob | **NO** — stdlib `pathlib.glob` is the right tool, no library needed |
| Lazy spawn + idle shutdown + reconnect | **NO** — ~40 lines on top of multilspy. SQLAlchemy `pool_pre_ping` is the mental model, not a library to import |
| Filesystem watching | **NO** — don't build it at all (Q3) |
| Plugin-host API | **N/A** — Claude Code doesn't expose one; file upstream FR (Q4) |

**Bottom line:** The hand-rolled bits in the draft (LSP client, path resolution, schema parsing) are exactly the bits where mature libraries exist. The remaining hand-rolled bits (cache walk, lazy-spawn glue) are 50–100 lines of idiomatic Python that no library will do better. Adopt **multilspy + platformdirs + pydantic**, don't pull in **pluggy**, **watchdog**, or a custom LSP client.

---

### Sources
- [VS Code Extension API — `vscode.extensions.all`](https://code.visualstudio.com/api/references/vscode-api)
- [Python `importlib.metadata` entry-points](https://docs.python.org/3/library/importlib.metadata.html)
- [pypa packaging guide — discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)
- [Neovim `nvim-lspconfig`](https://github.com/neovim/nvim-lspconfig); [lazy-load discussion #239](https://github.com/neovim/nvim-lspconfig/issues/239)
- [Microsoft `multilspy`](https://github.com/microsoft/multilspy)
- [Serena LSP integration architecture](https://deepwiki.com/oraios/serena/5-language-server-protocol-integration)
- [`mcp-language-server`](https://github.com/isaacphi/mcp-language-server); [`cclsp`](https://www.npmjs.com/package/cclsp)
- [MCP server lifecycle in Claude Code](https://code.claude.com/docs/en/mcp); [stdio idle-disconnect issue #1478](https://github.com/anthropics/claude-plugins-official/issues/1478); [no-auto-reconnect issue #43177](https://github.com/anthropics/claude-code/issues/43177)
- [SQLAlchemy connection pooling — `pool_pre_ping`](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [`watchdog` PyPI](https://pypi.org/project/watchdog/)
- [`platformdirs`](https://github.com/platformdirs/platformdirs)
