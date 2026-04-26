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

For local-development use today (v1.1 will publish a marketplace plugin):

```sh
git clone https://github.com/o2alexanderfedin/o2-scalpel.git
cd o2-scalpel
git submodule update --init --recursive
uvx --from ./vendor/serena serena-mcp
```

Or generate a per-language plugin tree via the Stage 1J generator:

```sh
uvx --from ./vendor/serena o2-scalpel-newplugin --language rust --out ./o2-scalpel-rust
uvx --from ./vendor/serena o2-scalpel-newplugin --language python --out ./o2-scalpel-python
```

See [`docs/install.md`](docs/install.md) for full setup including LSP server prerequisites (`rust-analyzer`, `pylsp`, `basedpyright-langserver`, `ruff`).

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
