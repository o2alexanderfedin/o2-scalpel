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

Built on top of the [Serena](https://github.com/oraios/serena) MCP server (forked as [`o2-scalpel-engine`](https://github.com/o2alexanderfedin/o2-scalpel-engine)), extended with a language-agnostic facade layer and per-language `LanguageStrategy` plugins. Rust + Python ship at v0.2.0.

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
