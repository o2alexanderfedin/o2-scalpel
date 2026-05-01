<p align="center">
  <img src="docs/assets/scalpel-banner.png" alt="Scalpel — semantic code surgery, by O2.services" width="720">
</p>

# o2.scalpel

LSP-driven semantic refactoring for agentic AI clients via the Model Context Protocol.

## Status

**v0.2.0** — Stage 3 ergonomic facades complete. **25 always-on MCP tools** ship as of `v0.2.0-stage-3-facades-complete`:

- **5 MVP facades** (Stage 2A): `scalpel_split_file`, `scalpel_extract`, `scalpel_inline`, `scalpel_rename`, `scalpel_imports_organize` + `scalpel_transaction_commit`.
- **12 Stage 3 Rust facades**: `convert_module_layout`, `change_visibility`, `tidy_structure`, `change_type_shape`, `change_return_type`, `complete_match_arms`, `extract_lifetime`, `expand_glob_imports`, `generate_trait_impl_scaffold`, `generate_member`, `expand_macro`, `verify_after_refactor`.
- **8 Stage 3 Python facades**: `convert_to_method_object`, `local_to_field`, `use_function`, `introduce_parameter`, `generate_from_undefined`, `auto_import_specialized`, `fix_lints`, `ignore_diagnostic`.

Plus the **8 Stage 1G primitives** (`scalpel_capabilities_list`, `scalpel_capability_describe`, `scalpel_apply_capability`, `scalpel_dry_run_compose`, `scalpel_rollback`, `scalpel_transaction_rollback`, `scalpel_workspace_health`, `scalpel_execute_command`) — total **34 always-on** tools.

The complete design report and all supporting research live under [`docs/`](docs/).

## What it is

A Claude Code plugin that exposes write/refactor operations from any installed Language Server Protocol server as MCP tools, complementing Claude Code's built-in (read-only) `LSP` umbrella tool.

- **Read** comes from Claude Code itself: `definition`, `references`, `hover`, `documentSymbol`, `callHierarchy`.
- **Write** comes from o2.scalpel: `codeAction`, `codeAction/resolve`, `applyEdit`, `rename`, `executeCommand`, plus 25 task-level ergonomic facades.

Built on top of the [Serena](https://github.com/oraios/serena) MCP server (forked as [`o2-scalpel-engine`](https://github.com/o2alexanderfedin/o2-scalpel-engine)), extended with a language-agnostic facade layer and per-language `LanguageStrategy` plugins.

## Supported languages (as of v1.9.9)

**23 languages**, each shipped as its own Claude Code plugin in the marketplace:

| Plugin | Language | LSP | Install |
|---|---|---|---|
| `o2-scalpel-rust` | Rust | rust-analyzer | `rustup component add rust-analyzer` |
| `o2-scalpel-python` | Python | pylsp + basedpyright + ruff | `pipx install python-lsp-server basedpyright ruff` |
| `o2-scalpel-markdown` | Markdown | marksman | `brew install marksman` (macOS) / `snap install marksman` (Linux) |
| `o2-scalpel-typescript` | TypeScript / JavaScript | vtsls | `npm install -g @vtsls/language-server` |
| `o2-scalpel-go` | Go | gopls | `go install golang.org/x/tools/gopls@latest` |
| `o2-scalpel-cpp` | C / C++ | clangd | `brew install clangd` / `apt install clangd` |
| `o2-scalpel-java` | Java | jdtls | `brew install jdtls` / `snap install jdtls --classic` |
| `o2-scalpel-csharp` | C# | csharp-ls | `dotnet tool install --global csharp-ls` |
| `o2-scalpel-lean` | Lean 4 | `lean --server` | via elan toolchain manager |
| `o2-scalpel-smt2` | SMT-LIB v2 | [dolmenls](https://github.com/Gbury/dolmen) (v0.10, diagnostics-focused) | pre-built binary download from GitHub Releases — see `scalpel_install_lsp_servers` |
| `o2-scalpel-prolog` | Prolog (SWI) | swipl-lsp | via SWI-Prolog pack manager |
| `o2-scalpel-problog` | ProbLog | (research-mode; inherits Prolog) | `pip install problog` |
| `o2-scalpel-haxe` | Haxe | haxe-language-server | `brew install haxe` + `npm install -g haxe-language-server` |
| `o2-scalpel-erlang` | Erlang | erlang_ls | `brew install erlang erlang_ls` |
| `o2-scalpel-ocaml` | OCaml | ocamllsp | `opam install ocaml-lsp-server` |
| `o2-scalpel-powershell` | PowerShell | PowerShell Editor Services (`pwsh`) | `brew install --cask powershell` |
| `o2-scalpel-systemverilog` | SystemVerilog | verible-verilog-ls | binary download from [chipsalliance/verible](https://github.com/chipsalliance/verible/releases) |
| `o2-scalpel-clojure` | Clojure | clojure-lsp | `brew install clojure-lsp/brew/clojure-lsp-native` |
| `o2-scalpel-crystal` | Crystal | crystalline | `brew install crystal crystalline` |
| `o2-scalpel-elixir` | Elixir | elixir-ls | `brew install elixir elixir-ls` |
| `o2-scalpel-haskell` | Haskell | haskell-language-server-wrapper | via [ghcup](https://www.haskell.org/ghcup/) — `ghcup install hls --set` |
| `o2-scalpel-perl` | Perl | Perl::LanguageServer | `cpanm Perl::LanguageServer` |
| `o2-scalpel-ruby` | Ruby | ruby-lsp | `gem install --user-install ruby-lsp` |

LSP installation can also be triggered from inside Claude via the `scalpel_install_lsp_servers` MCP tool (safety-gated: `dry_run=True` default + `allow_install=True` required for actual subprocess invocation).

### Engine-level language coverage (LSPs available without a dedicated plugin)

Beyond the 23 first-class plugins, the engine's `LanguageStrategy` registry exposes adapters for **29 additional languages** that can be driven via `serena start-mcp-server --language <name>` directly:

`al`, `ansible`, `bash`, `dart`, `elm`, `fortran`, `fsharp`, `groovy`, `hlsl`, `json`, `julia`, `kotlin`, `lua`, `luau`, `matlab`, `msl`, `nix`, `pascal`, `php`, `r`, `rego`, `scala`, `solidity`, `swift`, `terraform`, `toml`, `vue`, `yaml`, `zig`.

Plus alternate adapters for the same primary languages: `cpp_ccls`, `csharp_omnisharp`, `php_phpactor`, `python_jedi`, `python_ty`, `ruby_solargraph`, `typescript_vts`.

**Total: 52 languages addressable through O2 Scalpel** (23 with dedicated plugins + 29 engine-only). Adding a dedicated plugin for any engine-only language is one `o2-scalpel-newplugin <language>` invocation away.

## Relationship to Serena (what Scalpel adds)

**Scalpel is derived from [Serena](https://github.com/oraios/serena).** Serena already provides solid LSP-backed editing primitives — `RenameSymbolTool`, `ReplaceSymbolBodyTool`, `InsertBeforeSymbolTool`, `InsertAfterSymbolTool`, `SafeDeleteSymbol`, all marked `ToolMarkerSymbolicEdit` and routed through `LanguageServerCodeEditor` (real `textDocument/applyEdit` + LSP `TextEdit` lists, not text manipulation).

What Scalpel adds on top of that foundation:

| Layer | Serena (upstream) | Scalpel (this project) |
|---|---|---|
| **Symbol-level edits** | `rename_symbol`, `replace_symbol_body`, `insert_*_symbol`, `safe_delete_symbol` | (inherited from Serena — re-exposed unchanged) |
| **Task-level facades** | — | 33 `scalpel_*` tools: `split_file`, `extract`, `inline`, `change_visibility`, `organize_imports`, `tidy_structure`, `complete_match_arms`, `extract_lifetime`, `convert_to_async`, `annotate_return_type`, etc. — task-shaped wrappers around `textDocument/codeAction` + Serena's primitives. |
| **Languages out of the box** | Python, TypeScript, Go, Rust, Java, etc. (programming languages) | Adds **Markdown** as a first-class language (marksman LSP + 4 markdown facades) and ships **per-language Claude Code plugins** for Rust, Python, Markdown, TypeScript, Go, C/C++, Java, C#, Lean, SMT2, Prolog, ProbLog. |
| **LSP capability gating** | Static; assumes the LSP supports what's asked | **Dynamic capability discovery** (DLp0–DLp6): runtime `supports_method` / `supports_kind` consults the live `ServerCapabilities` + dynamic registrations. Pyright's missing `textDocument/implementation` returns a `CAPABILITY_NOT_AVAILABLE` envelope at dispatch time instead of a slow `SYMBOL_NOT_FOUND`. |
| **Distribution** | One MCP server, manual project config | **Claude Code marketplace** (`o2alexanderfedin/o2-scalpel`) with per-language plugins (`o2-scalpel-rust`, `o2-scalpel-python`, …) installable via `claude /plugin install`. |
| **LSP server installation** | Assumes LSPs are pre-installed on `$PATH` | `scalpel_install_lsp_servers` MCP tool (safety-gated: `dry_run=True` default + `allow_install=True` required) bootstraps marksman / rust-analyzer / pylsp / basedpyright / ruff / clippy / vtsls / gopls / clangd / jdtls / lean / csharp-ls / dolmenls / etc. via the right per-platform package manager (or pre-built binary download for dolmenls). |
| **E2E install verification** | — | `playground/{rust,python,markdown}/` workspaces + `make e2e-playground` + `.github/workflows/playground.yml` exercise the full marketplace-add → plugin-install → MCP-boot path against the live GitHub repo. |
| **Branding & UX** | Generic Serena MCP | Scalpel marketplace, `Alex Fedin & AI Hive®` author block, per-language READMEs with banner, generator-stamped provenance SHAs, `o2-scalpel-newplugin` CLI for adding new languages. |

In short: Scalpel = Serena's editing primitives + a task-shaped facade layer + first-class polyglot distribution + dynamic capability gating, packaged as Claude Code plugins.

## Install

Prerequisites:

```sh
# Claude Code >= 1.0.0 (the /plugin marketplace API was added in 1.0.0)
brew upgrade claude-code   # if upgrading from <1.0.0

# Rust plugin: rust-analyzer via rustup
rustup component add rust-analyzer
```

### Recommended: install via Claude Code's plugin manager

In Claude Code:

```
/plugin marketplace add o2alexanderfedin/o2-scalpel
/plugin install o2-scalpel-rust@o2-scalpel
/reload-plugins
```

This path fetches the engine (`o2-scalpel-engine`) automatically from
GitHub via the plugin's `.mcp.json` `git+URL` reference. No submodules
are cloned into your workspace.

To verify the install worked:

```
/scalpel_workspace_health
```

### Engine developers only: local-dev shortcut

This path is for contributors hacking on the engine itself
(`vendor/serena`). It bypasses the plugin manager and uses the in-tree
submodule directly:

```sh
git clone https://github.com/o2alexanderfedin/o2-scalpel.git
cd o2-scalpel
git submodule update --init --recursive
uvx --from ./vendor/serena serena-mcp --language rust
```

If you only want to *use* the plugin, prefer the recommended path above —
it does not require submodule recursion.

To verify all plugins locally:

```sh
make verify-plugins-fresh
```

See [`docs/install.md`](docs/install.md) for Python and Markdown plugins, and for `pylsp`,
`basedpyright-langserver`, `ruff`, and `marksman` setup.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Plugin not found in any marketplace` | Catalog stale or never added | `/plugin marketplace update o2-scalpel` or re-add with `/plugin marketplace add o2alexanderfedin/o2-scalpel` |
| `Executable not found in $PATH: rust-analyzer` | LSP not installed | `rustup component add rust-analyzer` |
| `Executable not found in $PATH: pylsp` | Python LSP not installed | `pipx install python-lsp-server` |
| `Executable not found in $PATH: marksman` | Markdown LSP not installed | `brew install marksman` |
| `applied=False` on a refactor | rust-analyzer not yet indexed | Run `cargo build` in the project once before retrying |
| `git+URL` install hangs | Network or GitHub auth issue | Check `~/.netrc` or SSH key; try `uvx --from git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git serena-mcp --help` directly |
| Plugin cache stale after re-publish at same version | `version: "1.0.0"` is pinned in cache | `/plugin uninstall o2-scalpel-rust` then reinstall, or bump `plugin.json` version |
| Skill / tool namespace not found after install | Claude Code < 1.0.0 | `brew upgrade claude-code` |
| Skill not appearing after plugin install | Plugins not reloaded | Run `/reload-plugins` in Claude Code |
| `verify-scalpel-rust.sh` exits with code 2 at SessionStart | `rust-analyzer` not on PATH — blocking error | Install via `rustup component add rust-analyzer`, then verify with `which rust-analyzer` |
| `make e2e-playground` skips every test | `rust-analyzer` or `cargo` missing on PATH | Install via `rustup`; verify with `which rust-analyzer` and `which cargo` |
| `cargo test` fails with `cannot open shared object file` | rustc dylib mismatch | Reinstall toolchain via `rustup toolchain install stable` |

## Verifying the install end-to-end

The repository ships Rust and Python playground workspaces and a programmatic
E2E suite that exercises five facades each against a real LSP process. To run
locally:

```sh
# Rust playground (requires rust-analyzer + cargo)
rustup component add rust-analyzer
make e2e-playground

# Python playground (requires pylsp + python3)
# Both Rust and Python tests run via the same target:
make e2e-playground
```

The Python playground (`playground/python/`) was added in v1.3-C and mirrors
the Rust playground structure. It exercises `scalpel_split_file`,
`scalpel_rename`, `scalpel_extract`, `scalpel_inline`, and
`scalpel_imports_organize` against a `pylsp`-backed Python project.

The Markdown playground (`playground/markdown/`) was added in v1.3-D and
covers the four Markdown facades: `scalpel_rename_heading` (marksman LSP,
including cross-file wiki-link propagation), `scalpel_split_doc`,
`scalpel_extract_section`, and `scalpel_organize_links` (the latter three
are pure-text and run without marksman).

The same script runs in CI on every push to `main` (see
`.github/workflows/playground.yml`).

> **Note — Phases 1–7 in progress**: the `playground/rust/` workspace,
> the `make e2e-playground` Makefile target, and the CI workflow are
> being built out as part of v1.2.2 Phases 1–7. Until those phases
> land, use `make verify-plugins-fresh` for local end-to-end
> verification. See
> [`docs/superpowers/specs/2026-04-28-rust-plugin-e2e-playground-spec.md`](docs/superpowers/specs/2026-04-28-rust-plugin-e2e-playground-spec.md)
> for the full playground spec and phase delivery schedule.

## Layout

```
.
├── docs/
│   ├── design/      Authoritative design reports + MVP scope report
│   ├── install.md   Setup + LSP-server prerequisites
│   └── superpowers/plans/
│                    Per-stage implementation plans + PROGRESS ledgers
├── vendor/
│   ├── serena/                          Fork — extension target (the engine)
│   ├── claude-code-lsps-boostvolt/      Fork — marketplace shape reference
│   └── claude-code-lsps-piebald/        Fork — analysis-only
├── o2-scalpel-rust/                     Generated per-language plugin tree
└── o2-scalpel-python/                   Generated per-language plugin tree
```

## Where to start

1. [Install guide](docs/install.md) — setup + LSP-server prerequisites
2. [MVP scope report](docs/design/mvp/2026-04-24-mvp-scope-report.md) — canonical contract for what ships and when
3. [Design report — Serena rust-analyzer refactoring extensions](docs/design/2026-04-24-serena-rust-refactoring-extensions-design.md)
4. [Open-questions resolution](docs/design/2026-04-24-o2-scalpel-open-questions-resolution.md)
5. [Stage 3 plan](docs/superpowers/plans/2026-04-26-stage-3-v0-2-0-ergonomic-facades.md) — most-recent implementation plan

## Capability discovery

The MCP catalog is auto-introspected from the per-language `LanguageStrategy` registry plus each LSP adapter's advertised `codeActionKind.valueSet`. Drift between the runtime catalog and the checked-in golden file is enforced by a CI gate:

```sh
cd vendor/serena
PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/spikes/test_stage_1f_t5_catalog_drift.py
# Refresh the baseline (after a rust-analyzer / basedpyright / ruff version bump):
PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/spikes/test_stage_1f_t4_baseline_round_trip.py --update-catalog-baseline
```

Catalog hash for external drift detection: `CapabilityCatalog.hash()` returns the SHA-256 of the canonical JSON.

## Origin

Spun out of `hupyy/hupyy-cpp-to-rust` on 2026-04-24 once it became clear the LSP-write capability is a general-purpose agentic-AI tool, not coupled to any specific transpiler project.

## License

To be determined for original code in this repo. Forks under `vendor/` retain their upstream licenses (Serena/o2-scalpel-engine: MIT, boostvolt: MIT, Piebald: not redistributable).
