# o2.scalpel install guide

> **STALE — last updated for v0.2.0 (2026-04-26).** The marketplace published in v1.1 (2026-04-27); the project is now at v1.7+ with 36 `scalpel_*` facades and the `PREFERRED:`/`FALLBACK:` docstring routing convention enforced by drift-CI (spec: `docs/superpowers/specs/2026-04-29-lsp-feature-coverage-spec.md`). The most current install path is `claude /plugins install o2-scalpel-<lang>@o2-scalpel` from the marketplace at `.claude-plugin/marketplace.json`. The local-checkout instructions below are still functional for engine development but are not the recommended user path.
>
> **Tool routing (applies regardless of install path):** prefer `scalpel_*` facades over upstream Serena primitives (`find_symbol`, `replace_symbol_body`, `insert_*_symbol`, `safe_delete_symbol`, `search_for_pattern`). Facade docstrings open with `PREFERRED:`; primitives do not — that asymmetry is the AST-fallback signal.

This document covers installing o2.scalpel for local development at **v0.2.0**. Marketplace publication is **v1.1** work — for now you install from a local checkout.

## Prerequisites

### Runtime
- **Python ≥ 3.10** (the engine targets 3.10–3.13).
- **uv** (`pip install uv` or [astral.sh/uv](https://docs.astral.sh/uv/) install). The MCP server runs via `uvx`.

### Language servers (install only the languages you need)

**Rust support** requires:
- `rust-analyzer` — `rustup component add rust-analyzer` or download from [rust-analyzer.github.io](https://rust-analyzer.github.io/manual.html#installation).
- `cargo` — for the `verify_after_refactor` facade and any e2e scenario that runs `cargo test`.

**Python support** requires three LSPs (each plays a distinct role per scope-report §6.3):
- `pylsp` (with the `pylsp-rope` plugin) — primary for refactors. `pip install python-lsp-server pylsp-rope`.
- `basedpyright-langserver` — type checking. `pip install basedpyright`.
- `ruff` — lint + import sort. `pip install ruff`.

Verify each is on `PATH`:

```sh
which rust-analyzer cargo pylsp basedpyright-langserver ruff
```

## Install

### 1. Clone the repo + submodules

```sh
git clone https://github.com/o2alexanderfedin/o2-scalpel.git
cd o2-scalpel
git submodule update --init --recursive
```

### 2. Set up the engine

```sh
cd vendor/serena
uv venv
uv pip sync  # or: uv pip install -e .
```

### 3. Run the MCP server (manual smoke-test)

```sh
uvx --from . serena-mcp
```

The server speaks JSON-RPC on stdio; pair it with a Claude Code config that registers it as an MCP server.

### 4. Generate per-language plugin trees (recommended for Claude Code)

Stage 1J ships a generator that emits `boostvolt`-shape plugin directories suitable for Claude Code's marketplace format:

```sh
cd ../..  # back to repo root
uvx --from ./vendor/serena o2-scalpel-newplugin --language rust --out ./o2-scalpel-rust
uvx --from ./vendor/serena o2-scalpel-newplugin --language python --out ./o2-scalpel-python
```

Each generated tree contains:
- `plugin.json` — Claude Code plugin manifest.
- `mcp.json` — MCP server registration.
- `marketplace.json` — boostvolt marketplace shape.
- `skills/` — per-facade skill files for capability hinting.
- `hooks/` — `SessionStart` hook stubs.

Reference these from your Claude Code `~/.claude/settings.json`.

## Verify

Run the spike-suite (no real LSP boot required):

```sh
cd vendor/serena
PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/spikes/ -q
```

Expected: **680 passed, 3 skipped** (at `v0.2.0-stage-3-facades-complete`).

Run the e2e harness (boots real LSPs; requires the prerequisites above):

```sh
PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/e2e/ -q -m e2e
```

Expected: 18+ passed; some scenarios skip when host `cargo` is broken (rustc dylib mismatch) or the relevant code-action isn't applied (Stage 3 long-tail E2E land in T6/T7).

## What ships at v0.2.0

**25 ergonomic facades + 8 always-on primitives = 34 always-on MCP tools.**

| Surface | Count | Tools |
|---|---|---|
| MVP facades (Stage 2A) | 6 | split_file, extract, inline, rename, imports_organize, transaction_commit |
| Stage 3 Rust (Wave A) | 4 | convert_module_layout, change_visibility, tidy_structure, change_type_shape |
| Stage 3 Rust (Wave B) | 4 | change_return_type, complete_match_arms, extract_lifetime, expand_glob_imports |
| Stage 3 Rust (Wave C) | 4 | generate_trait_impl_scaffold, generate_member, expand_macro, verify_after_refactor |
| Stage 3 Python (Wave A) | 4 | convert_to_method_object, local_to_field, use_function, introduce_parameter |
| Stage 3 Python (Wave B) | 4 | generate_from_undefined, auto_import_specialized, fix_lints, ignore_diagnostic |
| Stage 1G primitives | 8 | capabilities_list, capability_describe, apply_capability, dry_run_compose, rollback, transaction_rollback, workspace_health, execute_command |

Discover the full set at runtime:

```python
from serena.tools.scalpel_runtime import ScalpelRuntime
catalog = ScalpelRuntime.instance().catalog()
print(catalog.hash())  # SHA-256 of canonical JSON
```

## Out of scope at v0.2.0 (deferred)

- **Marketplace publication** at `o2alexanderfedin/claude-code-plugins` → v1.1.
- **TypeScript / Go / clangd / Java strategies** → v2+.
- **Stage 3 E2E** (E13-E16 Rust + E4/5/8/11-py Python) → ships shortly after the facades.
- **Stage 1H continuation** (28 per-assist-family integration tests + 17 RA companion crates + 3 calcpy sub-fixtures) → parallel workstream.
- **Long-tail nightly gates**: multi-crate (E5), crate-wide glob (E6), cold-start on 200+ crates (E7), crash-recovery (E8).

See [`docs/design/mvp/2026-04-24-mvp-scope-report.md`](design/mvp/2026-04-24-mvp-scope-report.md) §4.7 for the canonical out-of-scope matrix.

## Troubleshooting

### `serena-mcp` script entry not found

Run via `uvx --from .` (not bare `uvx serena-mcp`). Reason: the engine's `pyproject.toml` doesn't expose the script entry standalone.

### `cargo test` fails with `rustc_driver dylib not loadable`

Host toolchain corruption (commonly seen when `rustup` is interrupted mid-update). Re-install:

```sh
rustup self uninstall
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup component add rust-analyzer
```

### `pylsp-rope` integration tests fail

Pin `rope==1.14.0` (newer versions changed `MoveModule.get_changes()` signature; the engine's bridge handles 1.14 but not later majors).

### Capability catalog drift gate fails

Re-baseline after a known-good LSP version bump:

```sh
cd vendor/serena
PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest \
  test/spikes/test_stage_1f_t4_baseline_round_trip.py --update-catalog-baseline
```

Commit the regenerated `test/spikes/golden/catalog_baseline.json`.
