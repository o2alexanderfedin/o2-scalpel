# o2.scalpel Open Questions — Resolution Report

Status: report-only. Resolves Open Questions #10, #11, #12 of the main design report and adds a new resolution (Q13) on legal fork/rename feasibility for `claude-code-lsps`.

Cross-reference: [main design](2026-04-24-serena-rust-refactoring-extensions-design.md).

Date: 2026-04-24. Authors: synthesis from four specialist briefs (cache discovery + lazy spawn, marketplace location, two-process LSP cost, license/rename feasibility).

---

## Executive summary

| #   | Question                                | Decision                                                                                                                                                                      | Confidence |
| --- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Q10 | Cache-path stability and lazy spawn     | Adopt `multilspy` + `platformdirs` + `pydantic`. Resolve cache path through env-var → config-file → `platformdirs`-derived default → fail-loud chain. Snapshot once at startup; expose a `scalpel_reload_plugins` MCP tool. Lazy-spawn via SQLAlchemy `pool_pre_ping` analogue (per-language pool, `is_alive()` on checkout, transparent respawn, idle-shutdown after 10 min). | high       |
| Q11 | Marketplace publication location        | Multi-plugin marketplace repo `o2alexanderfedin/claude-code-plugins` containing `o2-scalpel/` (with `.mcp.json` + skills) plus a top-level `.claude-plugin/marketplace.json`. NOT a single-plugin repo. | high       |
| Q12 | Two-LSP-process resource cost           | Per-language Strategy mitigations (Rust: separate `cargo.targetDir`, lazy + idle-shutdown; Go: prefer `gopls -remote=auto`; C/C++: shared `--index-file=`; Python: do nothing). Add `O2_SCALPEL_LAZY_SPAWN=1` (default on) and `scalpel.lsp.<lang>.disable=true` opt-out for low-memory hosts. | medium     |
| Q13 (new) | Fork / rename feasibility of upstream `claude-code-lsps` repos | Boostvolt: fork + rename + redistribute (MIT, attribution required). Piebald: do **not** redistribute (no LICENSE → all rights reserved). Keep Piebald as private analysis-only submodule, file licensing-inquiry issue, clean-room re-author any Piebald-only manifests using upstream LSP docs as the data source. | high       |
| Q14 (new) | Should we ship our own bulk LSP-config plugins? | **No** — ship a single small **`o2-scalpel-newplugin`** template-generator tool (~100 LoC) instead of bulk-authoring ~30 plugins. Author 1–2 reference plugins by hand; users and contributors generate the rest on demand. Marketplace stays minimal; we never inherit ~30 plugins of upstream-tracking maintenance. | high       |

The five resolutions interlock. Q10 dictates the runtime data path (where scalpel finds `.lsp.json` files); Q11 dictates the distribution mechanism (where users install scalpel from); Q12 dictates the per-language runtime behaviour once an LSP descriptor is loaded; Q13 dictates which upstream marketplaces we may legally derive from when populating Q11's marketplace with peer LSP plugins; Q14 trumps the bulk-derivation question by replacing it with on-demand generation.

---

## Q10 — Cache-path stability and lazy spawn

The verified Claude Code layout today is `~/.claude/plugins/cache/<plugin>/<version>/.lsp.json` with a sibling `~/.claude/plugins/installed_plugins.json` manifest. The shape is stable enough to parse but is not a published public contract.

### Adopted libraries

Three Python libraries replace hand-rolled code that the original draft would otherwise carry:

- **[`multilspy`](https://github.com/microsoft/multilspy)** (Microsoft) — async LSP client wrapping JSON-RPC framing, stdio spawn, request routing, and lifecycle hooks. Already proven in Serena, which makes it the lowest-risk choice in scope. It does not idle-shutdown out of the box; we add ~40 lines on top.
- **[`platformdirs`](https://github.com/platformdirs/platformdirs)** — canonical resolver for `~/.claude` (and equivalent on Windows / Linux XDG paths). Replaces hand-coded path branches.
- **`pydantic` v2** — schema validation for `.lsp.json`. Fails loudly with a descriptive message and a link to the upstream tracker if the schema mutates upstream.

Specifically rejected: `pluggy` (over-fitted to importable Python plugins; we have arbitrary JSON), `watchdog` (see "Watch behaviour" below), and any hand-rolled LSP JSON-RPC client.

### Lazy-spawn pattern (concrete)

Mental model: SQLAlchemy connection pooling. ([SQLAlchemy `pool_pre_ping` docs](https://docs.sqlalchemy.org/en/20/core/pooling.html)). The scalpel server holds a `dict[(language, project_root), LSPClient]` registry. Behaviour:

1. **Lazy spawn on first use.** No LSP processes are started at MCP server boot. The first facade call referencing `.rs` triggers `_get_or_spawn(Language.RUST, project_root)`. This addresses the Claude-Code stdio-idle-disconnect issue ([anthropics/claude-plugins-official#1478](https://github.com/anthropics/claude-plugins-official/issues/1478) and [anthropics/claude-code#43177](https://github.com/anthropics/claude-code/issues/43177)) — if CC severs the stdio pipe, no expensive LSP processes have been wasted on a connection that no longer exists.
2. **Pre-checkout health probe.** Each call runs an `is_alive()` check: send `$/cancelRequest` for an unused id, expect a response within 50 ms; if `BrokenPipeError` / `ProcessLookupError` / timeout, drop the entry and respawn. This is the SQLAlchemy `pool_pre_ping` analogue; it is a deliberate small constant cost that eliminates a class of "stale-process" bugs.
3. **Idle shutdown.** A background `asyncio` task scans the registry every 60 s; entries idle longer than `O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS` (default 600) are gracefully shut down (`shutdown` request, 2 s wait, `SIGTERM`, `SIGKILL` fallback). Same shape Serena uses internally, reduced to a parameter.
4. **One process per (language, project_root).** Multiple files of the same language inside one workspace share an LSP. Multiple workspaces (multi-root MCP sessions) get separate LSPs because rust-analyzer cannot retarget its workspace cleanly mid-session.

### Cache-path mitigation chain

The discovery path is layered, in order:

1. `$O2_SCALPEL_PLUGINS_CACHE` environment variable (full override, primary escape hatch).
2. `[discovery].plugin_cache` key in `~/.config/o2.scalpel/config.toml` if present.
3. `platformdirs.user_data_dir("claude") / "plugins" / "cache"` — the cross-platform default.
4. Hard-coded fallback `~/.claude/plugins/cache` for legacy hosts.
5. If none of the above contains a single `.lsp.json` after a `glob("*/*/.lsp.json")`, fail loud with an actionable error listing every attempted path.

Each `.lsp.json` is parsed through a `pydantic` model. Schema drift surfaces immediately: scalpel logs the offending file, the failed field, and a permalink to the upstream tracker rather than swallowing and degrading silently. A fixture tree under `tests/fixtures/claude-cache/` snapshots the real layout so CI catches Anthropic-side restructures.

A long-term mitigation, separate from code: file an Anthropic feature request ("documented plugin-list API"). Low cost, possibly high payoff. Reference precedent: rust-analyzer formalized `experimental/serverStatus` along the same path.

### CC stdio-idle gotcha and how scalpel handles it

Claude Code currently closes idle stdio pipes on long-running MCP servers without auto-respawn ([anthropics/claude-code#43177](https://github.com/anthropics/claude-code/issues/43177)). Two scalpel-side consequences:

- The MCP server itself must not allocate expensive resources (LSPs, indexes) at boot — the lazy-spawn rule above is the answer.
- The `scalpel_reload_plugins` MCP tool exists not for filesystem-watch coverage but to give the user a deterministic way to refresh state after a `/reload-plugins` cycle without reconnecting the entire MCP layer.

### Watch behaviour

**No filesystem watcher.** Snapshot at startup; refresh on `scalpel_reload_plugins`. Reasoning: Claude Code itself requires `/reload-plugins` after install/disable ([code.claude.com/docs/en/mcp](https://code.claude.com/docs/en/mcp)); Serena, cclsp, and mcp-language-server all behave identically; `watchdog` adds threads, FSEvents/inotify complexity, and a dependency for a near-zero-value feature. The cost of being wrong is one user-visible reload step, which is acceptable.

---

## Q11 — Marketplace location

### Decision

Publish under **`o2alexanderfedin/claude-code-plugins`**. This is a multi-plugin marketplace repo, not the single-plugin layout proposed as default in the main spec.

### Repo layout (concrete)

```
o2alexanderfedin/claude-code-plugins/
├── .claude-plugin/
│   └── marketplace.json          # lists o2-scalpel, future plugins
├── o2-scalpel/
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json                 # registers o2-scalpel MCP server
│   ├── skills/                   # facade docs, LSP-write workflows
│   ├── hooks/
│   │   └── verify-scalpel.sh
│   └── README.md
└── (future plugins go here)
```

Installation flow for end users:

```
/plugin marketplace add o2alexanderfedin/claude-code-plugins
/plugin install o2-scalpel@o2alexanderfedin/claude-code-plugins
```

References: [Plugins reference](https://code.claude.com/docs/en/plugins-reference), [Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces).

### Migration trap analysis

Single-plugin repos work mechanically but bury two operational hazards. First, discoverability is poor — they do not surface in the official Discover tab or third-party aggregators (claudemarketplaces.com, ComposioHQ/awesome-claude-plugins). Second, migrating from `o2-scalpel-plugin` to `claude-code-plugins` after users have hardcoded the original URL forces an audible break in the install command. Every successful community marketplace today (boostvolt, Piebald, jeremylongshore, anthropics official) uses the multi-plugin layout. The "scalpel marketplace" can absorb a future `o2-trace`, `o2-bench`, or `o2-format` plugin without URL churn.

If Anthropic ships native LSP-write ([#24249](https://github.com/anthropics/claude-code/issues/24249), [#1315](https://github.com/anthropics/claude-code/issues/1315)), scalpel's value collapses to "supports languages CC's native write doesn't yet cover." The marketplace layout absorbs that deprecation cleanly — tag `v2.0-deprecated`, banner the README, keep installable but maintenance-only.

---

## Q12 — Two-LSP-process cost

The two-process tax cannot be eliminated in 2026 because (a) `rust-analyzer` has no daemon mode and no multi-client transport — only stdio ([rust-lang/rust-analyzer#4712](https://github.com/rust-lang/rust-analyzer/issues/4712), `S-unactionable, E-hard`), (b) no production-grade many-clients-to-one-LSP multiplexer exists (the closest, [`ifiokjr/lspee`](https://github.com/ifiokjr/lspee), is pre-1.0 and untested at scale; `joaotavora/lsplex` was archived 2025-12 with the upstream note "doesn't really do anything useful yet"), and (c) Anthropic's LSP-write roadmap is realistically 6–18 months out.

We commit to mitigating per-language. There is no clean global fix.

### Per-language Strategy mitigations

| Language     | Strategy                                                                                                                                                                                                                                                                                                                                                                          |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Rust**     | Lazy-spawn on first scalpel call; separate `rust-analyzer.cargo.targetDir = ${CLAUDE_PLUGIN_DATA}/ra-target` to avoid `cargo` lock contention with CC's rust-analyzer ([rust-analyzer config docs](https://rust-analyzer.github.io/book/configuration.html) — `cargo.targetDir` exists for exactly this reason); idle-shutdown after 10 min. `procMacro.enable=true` is non-negotiable on macro-heavy workspaces and is **not** part of the reduced-capability profile. Active memory tax: ~4–8 GB; cold-start: ~5 min. Acceptable on 32–64 GB dev machines. |
| **Go**       | Detect a running `gopls -remote=auto` daemon ([golang/go#78668](https://github.com/golang/go/issues/78668)); reuse it. Otherwise spawn fresh. This eliminates the two-process tax cleanly when the user already has a daemon (the canonical multi-client design upstream of every other major LSP).                                                                                                                                                                                |
| **C/C++**    | Pre-run `clangd-indexer` once to build a shared static index; both scalpel's clangd and CC's clangd point at the same `--index-file=path.idx` ([clangd indexing docs](https://clangd.llvm.org/design/indexing)). Live state still doubles but is small; the expensive portion (project-wide cross-references) is shared.                                                                                                                                                                                                  |
| **Python**   | No optimization. Pyright spawn is ~300 MB and sub-second. Two instances side-by-side cost less than the engineering time to share them. Optionally adopt the `typemux-cc` per-`.venv` routing pattern if the user's project layout creates `.venv` confusion.                                                                                                                                                                                                                       |
| **Other**    | Lazy-spawn + idle-shutdown defaults. Document the tax honestly in the strategy file.                                                                                                                                                                                                                                                                                                                                                                                                |

### Opt-in flag for low-memory hosts

The Rust mitigation is acceptable on 32–64 GB development machines. It is **not** acceptable on 16 GB laptops where two rust-analyzer instances will swap. Two flags address this:

- `O2_SCALPEL_LAZY_SPAWN=1` (default on, already in the main spec at OQ #12). Defers cost until the agent actually needs precision.
- `O2_SCALPEL_DISABLE_LANGS=rust` (or, equivalently, `scalpel.lsp.rust.disable=true` in `~/.config/o2.scalpel/config.toml`). When set, scalpel's facades return `failure: {kind: "language_disabled_by_user", hint: "..."}` for that language and the user falls back to CC's read-only LSP plus the standard `Edit` tool for writes. Strictly degraded but predictable.

### Honest verdict — when does this become unacceptable?

The two-process tax is a known-leaky workaround, not a clean solution. It becomes unacceptable when (a) the user runs on ≤16 GB RAM in a Rust workspace with ≥50 crates, or (b) scalpel runs on shared CI infrastructure where idling rust-analyzer eats slot budget. For (a) the opt-out flag is the answer; for (b) run scalpel in a per-job worker container, never as a long-running daemon — cold-start is the lesser cost in that mode. When Anthropic ships LSP-write (likely 2026 H2 / 2027 H1), scalpel's rust-analyzer can retire entirely.

---

## Q13 (new) — Fork / rename feasibility

The main spec implies, but does not address, that scalpel may want to fork upstream `claude-code-lsps` repos and rename them under the o2.services brand the way Serena was forked. The two upstreams differ in licensing posture, and the answer is not symmetric.

### Boostvolt

`boostvolt/claude-code-lsps` ships a verbatim **MIT** `LICENSE.md`, `Copyright (c) 2025 Jan Kott`. Confirmed by `gh repo view --json licenseInfo` (`{"key":"mit"}`) and by direct file read of the local clone.

MIT permits: fork, modify, rename, redistribute (source or binary), sublicense, relicense the combined work, commercial use. The only obligation is preserving the copyright + permission notice in all copies or substantial portions.

**Verdict: GREEN.** Proceed with the fork. Required attribution goes into the renamed repo's `LICENSE` (or `LICENSES/MIT-boostvolt.txt`) preserving the upstream notice verbatim, plus a one-line README credit:

> Originally based on [claude-code-lsps](https://github.com/boostvolt/claude-code-lsps) by Jan Kott (MIT). Renamed and extended by O2.services.

Branding caveat: do not put "boostvolt" or "Claude" / "Claude Code" (Anthropic marks) in the renamed product name. Use a neutral name such as `o2-lsp-marketplace` or `scalpel-lsps`.

### Piebald

`Piebald-AI/claude-code-lsps` has **no LICENSE file** at any depth. Confirmed four ways: filesystem walk of the local clone (only `README.md`, `CLAUDE.md`, `.gitignore`, plugin dirs), `gh repo view --json licenseInfo` returns `licenseInfo: null`, no top-level `license` field in `.claude-plugin/marketplace.json`, and the `"license": "MIT"` / `"Apache-2.0"` strings inside per-plugin `plugin.json` files describe the *underlying LSP binaries* (clangd, rust-analyzer), not Piebald's manifest code.

Per [GitHub's licensing documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository): without a license, the default copyright laws apply, meaning Piebald LLC retains all rights. GitHub TOS §D.5 grants every user a license to fork and view public content **on the GitHub platform** — that does not extend to renaming, redistribution outside GitHub, or relicensing. There is no reliable "implicit license" doctrine that would help us redistribute.

**Verdict: RED for redistribution, YELLOW for inspiration.** Do not rename and ship. Do not include Piebald content in any public release artifact (npm/cargo/pip package, marketplace JSON, release tarball). Keeping the upstream as a read-only submodule under `vendor/` strictly for private analysis is allowed.

### Operational rule for the repo

Codify the asymmetry in `vendor/README.md`:

- `vendor/claude-code-lsps-boostvolt/` — MIT, redistributable, attribution preserved in `LICENSES/MIT-boostvolt.txt`.
- `vendor/claude-code-lsps-piebald/` — no license, **private analysis only — not distributed**. Excluded from any release tarball/sdist via `.gitattributes export-ignore` or equivalent. CI must verify (a single grep on the published tarball is sufficient).

For any LSP server that exists in Piebald but not Boostvolt (`ada-language-server`, `phpactor`, `texlab`, `metals`, `julia-lsp`, `kotlin-lsp`, `lean4-*`, `omnisharp`, `solidity-language-server`, `svelte`, `vue-volar`, `vtsls`), **clean-room re-author** the manifest using Boostvolt's MIT plugin structure as the template and the upstream LSP project's own docs as the data source. The set of supported languages and the choice of LSP binary is uncopyrightable factual information; only the textual expression is protected. Track each re-authored file with a commit message of the form `feat(lsp): add ada-language-server plugin (clean-room, no Piebald content)`.

### Draft licensing-inquiry issue text

File against `Piebald-AI/claude-code-lsps`, verbatim:

> **Title:** Please add a LICENSE file
>
> Hi Piebald team — thanks for publishing claude-code-lsps; the breadth of LSP coverage is great.
>
> We noticed the repository does not currently include a LICENSE file, and `gh repo view` reports no detected license. Per [GitHub's licensing docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository), this defaults to "all rights reserved", which makes it difficult for downstream projects (including ours, an open-source C++ to Rust transpiler tooling project) to depend on or extend the marketplace.
>
> Would you consider adding a permissive license such as MIT or Apache-2.0? We'd be glad to open a PR adding the file if you tell us your preference. If MIT works, the canonical text would be:
>
> ```
> MIT License
> Copyright (c) 2025 Piebald LLC
> ...
> ```
>
> Either way, thank you for the work — and a clear license would let the community contribute back additional language plugins.

Track the issue ID; revisit before each public release. If MIT/Apache-2.0 is granted, switch from clean-room re-authoring to direct fork + attribution.

**Disclaimer.** This analysis was performed by engineers reviewing public license texts and GitHub's published policies. **Not legal advice.** Before any commercial release of o2.scalpel that bundles or redistributes either upstream, route the result through counsel for (a) the MIT attribution chain for Boostvolt, (b) the licensing status of any Piebald-derived content, and (c) the trademark posture of the renamed product (especially "Claude", "Claude Code", "Anthropic").

---

## Q14 (new) — On-demand plugin generation instead of bulk authoring

### Premise

Each LSP plugin in the boostvolt/Piebald marketplaces is ~80–150 LoC of pure data: a `.lsp.json` (5–15 lines), a `plugin.json` (~10 lines), an optional `hooks/check-<lang>.sh` (30–50 lines), and an optional `hooks/hooks.json` (~12 lines). Across both upstreams there are roughly 50 unique languages. Bulk re-authoring is mechanical translation from upstream LSP server READMEs — small per plugin, medium in aggregate (~3,660 LoC across ~120 files), low novelty, **but with permanent maintenance debt** (init options drift, install paths churn across platforms, new servers appear).

### Decision

**Do not bulk-author.** Ship a small CLI: **`o2-scalpel-newplugin`**.

```
o2-scalpel-newplugin <lang> <binary> <ext>[,<ext2>,...]
                     [--install-hint "brew install …"]
                     [--init-options path/to/options.json]
                     [--marketplace path/to/o2alexanderfedin-claude-code-plugins]
```

Generates a complete plugin directory in 30 seconds. Single source of truth: a Jinja-style template inside scalpel's repo at `templates/lsp-plugin/`. ~100 LoC of Python (or bash) plus the templates themselves.

Maintained reference plugins: **two**, hand-authored, used as the canonical examples and as fixtures for the generator's smoke test. Likely candidates: `rust-analyzer` (medium-complexity init options) and `clangd` (trivial config). Together these exercise every template branch.

### Layout

```
o2alexanderfedin/claude-code-plugins/        # the o2 marketplace repo
├── .claude-plugin/marketplace.json           # lists o2-scalpel + reference plugins + generator
├── o2-scalpel/                               # the MCP-server plugin (write capability)
├── rust-analyzer-reference/                  # hand-authored, generator self-test
├── clangd-reference/                         # hand-authored, generator self-test
└── tools/
    ├── o2-scalpel-newplugin                  # the CLI entry point
    └── templates/lsp-plugin/                 # Jinja template tree
        ├── .claude-plugin/plugin.json.j2
        ├── .lsp.json.j2
        ├── hooks/check-{{lang}}.sh.j2
        ├── hooks/hooks.json.j2
        └── README.md.j2
```

### Why this is strictly better than bulk authoring

- **Maintenance scales to zero.** We ship two plugins, not thirty. New languages appear when needed; we don't pre-author dead inventory.
- **Drift is the user's problem, not ours.** When rust-analyzer changes init options, the user regenerates with `--init-options new.json`. We don't have to track every upstream's release cadence.
- **Contribution path is trivial.** Anyone can open a PR adding a generated plugin to the marketplace; the generator guarantees consistency.
- **Sidesteps the licensing constraint.** No language description is copied from boostvolt or Piebald. The `command` and `extensionToLanguage` fields come from upstream LSP server docs (uncopyrightable facts: "rust-analyzer is the binary; .rs is the extension"). The `hooks/check-<lang>.sh` is generated from a template authored in-house.
- **Shrinks Q13's blast radius.** The "clean-room re-author" recommendation for Piebald-only languages becomes a one-line generator invocation per language.

### Generator behaviour

The CLI does:

1. Resolves language metadata: takes the `<lang>` arg, validates against an in-tree allowlist of known LSP servers (sourced from upstream LSP server docs, not from boostvolt/Piebald), or accepts an `--unknown-lang-ok` flag for experimental servers.
2. Detects platform-specific install hints. macOS → brew, Linux → apt/cargo/npm based on binary, Windows → scoop/winget. Hint text comes from upstream READMEs.
3. Renders the template tree into `<marketplace>/<lang>/`.
4. Updates `<marketplace>/.claude-plugin/marketplace.json` to register the new plugin.
5. Validates the result: parses every JSON, lints the bash, executes `--help` on the configured binary if present.
6. Prints a one-line summary and the next-step command (`/plugin marketplace refresh`).

### Boundaries

- The generator is a developer/contributor tool, not an end-user feature. End users `/plugin install` from the marketplace; they do not run the generator.
- The two reference plugins are released as part of the marketplace. Generated plugins not committed back to the marketplace stay private to whoever generated them.
- The generator does **not** read `vendor/claude-code-lsps-boostvolt/` or `vendor/claude-code-lsps-piebald/` at any point — neither at build nor at runtime. This is the clean-room boundary that keeps Piebald off-limits even by accident. A pre-commit hook in the marketplace repo enforces this with a path-grep over the generator source.

### Effort

- Template tree (5 `.j2` files): small, ~150 LoC total
- Generator CLI (Python, click-based): small, ~100 LoC
- Two reference plugins (rust-analyzer + clangd): small, ~250 LoC together
- Generator smoke test (round-trips reference plugins through the templates): small, ~80 LoC
- Marketplace `marketplace.json` aggregator: trivial, ~40 LoC
- **Total: ~620 LoC across ~15 files. Complexity: small. Risk: low.**

### Compared to the three earlier paths

The three paths in the earlier analysis were: (A) piggyback only — 0 LoC, depends on third-party marketplaces; (B) hybrid — ~1,400 LoC, ~14 clean-room Piebald-only plugins shipped; (C) full marketplace — ~3,660 LoC, all 30 plugins re-authored.

Q14's generator path is **A + ~620 LoC**: piggyback at runtime, generator + two reference plugins on the side. Replaces the rationale for B and C entirely.

---

## Concrete amendments to the main spec

The following edits should be applied to `2026-04-24-serena-rust-refactoring-extensions-design.md` in a follow-up commit. Each is a precise replacement.

1. **Open Question #10 (line 818).** Replace the entire bullet with:

   > **Sibling-LSP discovery cache path.** Resolved (see [open-questions-resolution](2026-04-24-o2-scalpel-open-questions-resolution.md) §Q10). Discovery uses a layered chain (`$O2_SCALPEL_PLUGINS_CACHE` → `~/.config/o2.scalpel/config.toml` → `platformdirs.user_data_dir("claude")/plugins/cache` → hardcoded fallback → fail loud), schemas validated by `pydantic`, no filesystem watcher (refresh via `scalpel_reload_plugins` MCP tool), LSP processes spawned lazily through `multilspy` with a SQLAlchemy `pool_pre_ping`-style health probe and 10-min idle-shutdown.

2. **Open Question #11 (line 819).** Replace with:

   > **Where to publish the `o2-scalpel` plugin.** Resolved (§Q11). Multi-plugin marketplace at `o2alexanderfedin/claude-code-plugins` containing `o2-scalpel/` (with `.mcp.json` + skills) plus a top-level `.claude-plugin/marketplace.json`. Single-plugin layout was rejected on discoverability and migration-trap grounds.

3. **Open Question #12 (line 820).** Replace with:

   > **Two-LSP-process resource cost.** Resolved (§Q12). Per-language Strategy mitigations: Rust uses separate `cargo.targetDir` + lazy-spawn + idle-shutdown; Go reuses `gopls -remote=auto` daemon when available; C/C++ shares `clangd --index-file=`; Python does nothing. Two opt-out env vars: `O2_SCALPEL_LAZY_SPAWN=1` (default on) and `O2_SCALPEL_DISABLE_LANGS=<csv>` for low-memory hosts.

4. **Add a new Open Question #13 immediately after #12.** Insert:

   > 13. **Fork / rename feasibility for upstream `claude-code-lsps` marketplaces.** Resolved (§Q13). Boostvolt: fork + rename + redistribute (MIT, attribution required). Piebald: no LICENSE → all rights reserved; private analysis only, file licensing-inquiry issue, clean-room re-author Piebald-only manifests using upstream LSP docs as the data source. `vendor/claude-code-lsps-piebald/` excluded from release tarballs.

5. **Section "Sibling-plugin LSP discovery" (line 442).** After the path glob `~/.claude/plugins/cache/**/.lsp.json`, insert:

   > Path resolution uses `platformdirs.user_data_dir("claude")` (cross-platform), with override chain `$O2_SCALPEL_PLUGINS_CACHE` → `~/.config/o2.scalpel/config.toml` → `platformdirs` default → hardcoded fallback. Schemas are validated through `pydantic` v2 models; mismatches fail loud with an actionable error. See [open-questions-resolution](2026-04-24-o2-scalpel-open-questions-resolution.md) §Q10.

6. **Section "Two-LSP-process problem and mitigation" (line 482).** Append after the existing per-language bullet list:

   > Rust on a 227-crate workspace pays ~4–8 GB RAM and ~5 min cold-start. This is acceptable on 32–64 GB dev machines, **not** on 16 GB laptops — set `O2_SCALPEL_DISABLE_LANGS=rust` (or `scalpel.lsp.rust.disable=true`) to fall back to CC's read-only LSP plus standard `Edit` for writes. Go strategy reuses `gopls -remote=auto` daemon when available; C/C++ strategy shares a pre-built `clangd --index-file=`. See [open-questions-resolution](2026-04-24-o2-scalpel-open-questions-resolution.md) §Q12.

7. **`.mcp.json` block (line 422).** Add `O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS` and `O2_SCALPEL_PLUGINS_CACHE` to the `env` table as documented (commented) optional overrides:

   ```json
   "env": {
     "O2_SCALPEL_DISCOVER_SIBLING_LSPS": "1",
     "O2_SCALPEL_LAZY_SPAWN": "1"
     // optional: O2_SCALPEL_PLUGINS_CACHE, O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS, O2_SCALPEL_DISABLE_LANGS
   }
   ```

8. **Appendix D — References (line 961).** Add the following entries:

   > - multilspy (Microsoft): https://github.com/microsoft/multilspy
   > - platformdirs: https://github.com/platformdirs/platformdirs
   > - SQLAlchemy connection pooling — `pool_pre_ping`: https://docs.sqlalchemy.org/en/20/core/pooling.html
   > - rust-analyzer #4712 (persistent caches): https://github.com/rust-lang/rust-analyzer/issues/4712
   > - golang/go #78668 (gopls multi-workspace daemon): https://github.com/golang/go/issues/78668
   > - clangd indexing design: https://clangd.llvm.org/design/indexing
   > - Plugin marketplaces (Claude Code): https://code.claude.com/docs/en/plugin-marketplaces
   > - GitHub licensing docs: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

---

## Open follow-ups

These are genuinely open after this round.

- **Anthropic feature request for plugin-list API.** No tracking issue exists in `anthropics/claude-plugins-official` for a documented list-installed-plugins API. Filing it costs nothing and has positive expected value; the issue title should be specific (e.g., "Public API: list installed plugins and their cache directories"). Track the issue ID once filed.
- **Piebald licensing-inquiry response.** Outcome is binary (license added vs. silence). The clean-room re-authoring track proceeds in parallel and is not blocked on the response. Re-evaluate before the first public scalpel release.
- **`gopls -remote=auto` MCP-multi-workspace fix.** [golang/go#78668](https://github.com/golang/go/issues/78668) is open. The Go strategy's daemon path is correct in principle but degrades to the per-workspace stdio path until that issue closes. Watch the issue; flip the strategy when the fix lands.
- **`lspee` maturity.** [`ifiokjr/lspee`](https://github.com/ifiokjr/lspee) is the architecturally-correct many-clients-to-one-server multiplexer but is pre-1.0. If it reaches a tagged 1.0 with a non-trivial test suite before scalpel v2, revisit the two-process problem with shared-server in scope.
- **Anthropic native LSP-write.** Tracked at [anthropics/claude-code#24249](https://github.com/anthropics/claude-code/issues/24249), [#1315](https://github.com/anthropics/claude-code/issues/1315), and [#32502](https://github.com/anthropics/claude-code/issues/32502). The third is marked `stale`. Realistic horizon is 6–18 months. Scalpel's deprecation plan (Q11) is ready when it lands.
- **`vendor/` exclusion CI guard.** A simple grep over the published sdist/wheel verifying that `claude-code-lsps-piebald` content is absent is non-trivially correct (path normalisation across platforms, content vs. paths, etc.). Implement the guard before the first public release; treat the guard's existence as a release-blocker.

---

## Appendix A — Specialist sources

- **01 — cache discovery + lazy spawn** (1478 words). `/tmp/brainstorm-oq/01-cache-discovery-and-lazy-spawn.md`. Plugin-discovery ecosystem survey, lazy-spawn survey, `multilspy` recommendation, `pool_pre_ping` mental model, no-watcher precedent.
- **02 — marketplace** (1100 words). `/tmp/brainstorm-oq/02-marketplace.md`. Marketplace inventory, single-vs-multi-plugin trade-off, MCP-bearing plugin patterns, Anthropic-native-LSP-write contingency, recommended layout.
- **03 — two-process problem** (1359 words). `/tmp/brainstorm-oq/03-two-process-problem.md`. Per-server multi-client survey, LSP-multiplexer GitHub survey, index-only sharing analysis, Anthropic LSP-write roadmap signal (HN [46355165](https://news.ycombinator.com/item?id=46355165), CC #32502 stale).
- **04 — license** (1193 words). `/tmp/brainstorm-oq/04-license-rename-feasibility.md`. Boostvolt MIT verification, Piebald no-LICENSE verification, GitHub TOS §D.5 distinction, trademark posture, clean-room strategy, licensing-inquiry draft.

Tensions resolved during synthesis:

- **Brief 02 vs. main spec OQ #11 default.** Main spec defaults to standalone single-plugin (`o2-scalpel-plugin`); brief 02 recommends multi-plugin marketplace. Resolved in favour of brief 02: migration-trap and discoverability arguments make standalone the worse choice.
- **Brief 02's "fork Piebald as fallback" vs. brief 04's licensing posture.** Brief 02 floats forking either boostvolt or Piebald; brief 04 establishes Piebald cannot be redistributed. Resolved in favour of brief 04: Piebald path closed for redistribution; only Boostvolt forking remains.
- **Brief 03's `procMacro.enable=false` reduced-capability profile.** Listed as a memory-saving option but flagged lossy. Excluded from the Q12 mitigations table — the 227-crate hupyy workspace is macro-heavy; the option would silently break symbol resolution.
