# Existing E2E + Verify Patterns

**Researcher**: Agent A (patterns)
**Date**: 2026-04-28

## TL;DR (3 bullets)

- All existing E2E and smoke tests run against **in-tree local-path code** (`uvx --from ./vendor/serena`). No test exercises the published `git+https://github.com/o2services/o2-scalpel.git#subdirectory=vendor/serena` URL that a real user's `.mcp.json` contains.
- The verify hook (`hooks/verify-scalpel-rust.sh`) only checks that `rust-analyzer` is on PATH — it does NOT boot the MCP server, does NOT call `tools/list`, and does NOT validate that the plugin tree itself is well-formed.
- There is zero CI on the parent repo (`o2-scalpel`). The only CI workflows exist inside `vendor/serena` (upstream Serena's own pytest + CodeQL + Docker), and none of those workflows exercise the plugin-install path.

---

## 1. scripts/stage_1i_uvx_smoke.sh

**What it does:**

Accepts one argument (`<language>`), locates `o2-scalpel-<lang>/.mcp.json`, confirms the MCP server name matches `scalpel-<lang>`, then runs:

```sh
uvx --from "${REPO_ROOT}/vendor/serena" serena-mcp --language "${LANG_ARG}"
```

It sends three JSON-RPC messages on stdin (`initialize` → `notifications/initialized` → `tools/list`) with a 30-second timeout, and prints each tool name on stdout. Exits non-zero if `uvx` fails, times out, or produces no `tools/list` response.

**What it verifies:**
- `uvx` can install and launch the engine from the **local checkout** of `vendor/serena`.
- The MCP server key in `.mcp.json` follows the `scalpel-<lang>` naming convention.
- The server starts and responds to `tools/list` within 30 s.

**What it does NOT cover:**
- Installing from the published `git+https://...` URL (what a real user's `.mcp.json` does).
- Whether `rust-analyzer` is available (precondition, not checked here).
- Whether any tool actually works — only that the tool names are present in the manifest.
- The `markdown` language (Makefile's `verify-plugins-fresh` calls rust + python only).

---

## 2. scripts/dev_env_shim.sh

**What it does:**

A one-liner sourced shim. Sets `O2_SCALPEL_LOCAL_HOST=1` in the developer's shell. When this variable is active, a pytest conftest plugin (`test.conftest_dev_host`) forces `CARGO_BUILD_RUSTC=rustc` into the test process and any spawned rust-analyzer subprocess. This works around developer machines where `~/.cargo/config.toml` has `[build] rustc = "rust-fv-driver"` (a broken Rust-FV wrapper).

**What it does NOT cover:**
- Not relevant to CI or external install paths.
- Not sourced automatically — dev must remember to run `. ./scripts/dev_env_shim.sh` before `uv run pytest`.
- Has no effect on plugin install correctness.

---

## 3. Makefile targets

| Target | Purpose | Touches install? | Catches "fresh install fails"? |
|---|---|---|---|
| `generate-plugins` | Re-runs `o2-scalpel-newplugin` for rust+python+markdown, writes `marketplace.json`, restamps `_generator` banner | No — rewrites local tree | No |
| `generate-rust` | Single-language emit: `o2-scalpel-rust/` | No | No |
| `generate-python` | Single-language emit: `o2-scalpel-python/` | No | No |
| `generate-markdown` | Single-language emit: `o2-scalpel-markdown/` | No | No |
| `verify-plugins-fresh` | Runs `stage_1i_uvx_smoke.sh rust` + `stage_1i_uvx_smoke.sh python` | `uvx --from ./vendor/serena` (local, not GitHub) | No — wrong URL, markdown excluded |
| `_restamp-banners` | Internal: injects `_generator` key with current submodule SHA into 6 JSON files | No | No |
| `help` | Prints target summary | No | No |

Key observation: `verify-plugins-fresh` uses `--from <local-path>` while the shipped `.mcp.json` uses `--from git+https://...`. The Makefile does not exercise the published URL at all.

---

## 4. E2E test suite

**Location:** `vendor/serena/test/e2e/`

**Harness shape:**

The conftest (`test/e2e/conftest.py`) boots a `ScalpelRuntime` singleton against **four real LSP processes** (rust-analyzer, pylsp, basedpyright, ruff) discovered via `shutil.which`. It uses per-test `tmp_path` clones of two fixture projects:
- `fixtures/calcrs_e2e/` — minimal Rust Cargo workspace (`lib.rs`, `ops.rs`)
- `fixtures/calcpy_e2e/` — minimal Python package

The `_McpDriver` class instantiates tool classes directly by bypassing `__init__` via `cls.__new__()` and monkeypatching `get_project_root`. There is no MCP stdio layer in the E2E path — it calls Python tool `.apply()` methods directly.

**Opt-in gate:** tests are skipped unless `O2_SCALPEL_RUN_E2E=1` or `pytest -m e2e`. Binary prerequisites (`cargo`, `rust-analyzer`, `pylsp`, `basedpyright-langserver`, `ruff`) are individually `pytest.skip`-ed if missing.

**Scenario coverage (16 test modules):**
- E1: Rust 4-way split + Python split
- E2: dry-run commit
- E3: rollback
- E9: semantic equivalence
- E10: cross-file rename
- E11: workspace boundary
- E12: transaction commit/rollback
- E13–E16: Stage 3 Rust + Python facades
- Q3: catalog gate blind spots
- Q4: workspace boundary integration
- wall-clock budget (< 12 min aggregate)

**Are these run against installed plugins?** No. They run against in-tree Python code imported directly. There is no `uvx` invocation, no `.mcp.json` parsing, no MCP transport. A published-URL install failure would be completely invisible to this suite.

---

## 5. o2-scalpel-rust plugin tree contents

| File | Purpose |
|---|---|
| `.claude-plugin/plugin.json` | Claude Code marketplace manifest: name, version, description, author, tags, homepage, repository. All fields static. No `hooks` key — hook wiring is in `.mcp.json` indirectly via Claude's plugin loader. |
| `.mcp.json` | MCP server invocation config: `command: uvx`, `args: ["--from", "git+https://github.com/o2services/o2-scalpel.git#subdirectory=vendor/serena", "serena-mcp", "--language", "rust"]`. This is what a real user install exercises. |
| `README.md` | Generated docs: install command (`claude plugin install o2-scalpel-rust --from o2-scalpel`), requirements (Claude Code >= 1.0.0, `rust-analyzer` on PATH, `.rs` extensions), facade table, skills note, license. |
| `hooks/verify-scalpel-rust.sh` | SessionStart hook. Checks `command -v rust-analyzer`. Prints ready message or exits 1 with install hint (`rustup component add rust-analyzer`). Does NOT ping the MCP server. |
| `skills/using-scalpel-rename-symbol-rust.md` | Skill prompt: triggers `scalpel_rename_symbol` when user says "rename this" / "refactor name". Shows JSON tool call template. |
| `skills/using-scalpel-split-file-rust.md` | Skill prompt: triggers `scalpel_split_file` when user says "split this file" / "extract symbols". Shows JSON tool call template. |

Notable: the plugin tree ships only **2 skills** (rename + split) despite the engine exposing 12 Rust facades + 8 primitives. The generator emits skill files only for facades registered in the strategy's skill-hint list. The gap between 2 skills and 14+ tools is architectural — generator-driven, not accidental.

---

## 6. Current README install section

Quoted verbatim:

```
## Install

For local-development use today (v1.1 will publish a marketplace plugin):

    git clone https://github.com/o2alexanderfedin/o2-scalpel.git
    cd o2-scalpel
    git submodule update --init --recursive
    uvx --from ./vendor/serena serena-mcp

Or generate a per-language plugin tree via the Stage 1J generator:

    uvx --from ./vendor/serena o2-scalpel-newplugin --language rust --out ./o2-scalpel-rust
    uvx --from ./vendor/serena o2-scalpel-newplugin --language python --out ./o2-scalpel-python

See [docs/install.md](docs/install.md) for full setup including LSP server
prerequisites (rust-analyzer, pylsp, basedpyright-langserver, ruff).
```

**What it shows:**
- Local dev clone + submodule init
- Raw `serena-mcp` boot (bypasses the plugin tree entirely)
- Plugin tree regeneration (not install)

**What it omits:**
- How to install the plugin into Claude Code (`claude plugin install`)
- How to use the generated `.mcp.json` as a user
- No Cargo / rustup install step
- No `rustup component add rust-analyzer` step
- No step-by-step for the `git+https://...` URL path that `.mcp.json` uses
- No troubleshooting section (what to do if `rust-analyzer` is not found, if `uvx` fails, if the GitHub URL times out)
- No version pinning advice (the `.mcp.json` has no `@ref` or `@tag` — it will always pull the default branch tip)

---

## 7. CI surface

**Parent repo (`o2-scalpel`):** No `.github/` directory. Zero CI.

**`vendor/serena` submodule:** Has `.github/workflows/`:
- `pytest.yml` — upstream Serena's own test suite
- `codeql.yml` — static analysis
- `docker.yml` — Docker image build
- `codespell.yml` — spell check
- `publish.yml` — PyPI publish

None of these workflows exercise:
- The plugin install path
- `uvx --from git+https://...` against the published URL
- `hooks/verify-scalpel-rust.sh`
- Claude Code plugin loading

**Summary:** The project has no CI that catches "user installs from GitHub and it doesn't work."

---

## 8. Prior art

**Stage 1I plan** (`docs/superpowers/plans/2026-04-24-stage-1i-plugin-package.md`) explicitly deferred T12 ("uvx install + tools/list verify") because `serena-mcp` script entry didn't exist yet. The plan notes: *"T12: uvx install + tools/list verify deferred (serena-mcp script entry doesn't exist yet — Stage 1I follow-up)"*.

**Stage 1J memory** confirms the same: T12 was deliberately not executed.

**MVP cut memory** notes: distribution is `uvx --from <local-path>` at MVP. Marketplace publication is v1.1 work. The MVP cut explicitly acknowledged the E1/E10/E13-py test skips were due to host-cargo and LSP-startup gaps — not install-path gaps.

**v1.1 milestone memory** (`project_stream_5_v11_milestone.md`): marketplace publication landed but references `o2alexanderfedin/claude-code-plugins`, and deferred follow-ups included *"marketplace.json reconciliation"* and *"cross-process tmp-file race"* — no playground repo mentioned.

**v1.2 memory** (`project_v1_2_installer_marketplace_complete.md`): collapsed `marketplace.surface.json` into `marketplace.json`, added 5 LSP installers. No playground repo decision recorded.

**No prior decision record** exists for a separate "playground repo" or "fresh-install E2E" smoke repo. This would be net-new infrastructure.

---

## Gaps the playground would close

- **Published URL never exercised.** The `.mcp.json` `git+https://github.com/o2services/o2-scalpel.git#subdirectory=vendor/serena` URL is untested. Any packaging regression (wrong subdirectory, missing `pyproject.toml` entry, `serena-mcp` script missing) would only be discovered by a real user.
- **No CI at parent-repo level.** A playground repo with its own CI would provide the first automated signal that the published install path works.
- **Hook correctness gap.** `verify-scalpel-rust.sh` only checks `rust-analyzer` binary presence. It does not confirm the MCP server actually boots with the current published code. A full smoke (start + `tools/list`) is missing.
- **Version pinning.** `.mcp.json` always pulls the default branch tip. A playground repo could test pinned ref installs and catch breaking changes before they reach users.
- **Skill coverage.** Only 2 of 12+ Rust tools have skills. A playground repo's test matrix could surface which tools need skill files added.
- **`markdown` excluded from `verify-plugins-fresh`.** The Makefile's smoke target skips the markdown plugin entirely.
- **No "cold uvx cache" test.** All current tests assume `uvx` has a warm cache or a local path. A playground repo on a fresh CI runner would catch first-install cold-start issues (network, hash mismatches, missing transitive deps).

---

## Open questions for the synthesis pair

1. **Repo location.** Should the playground be a subdirectory in `o2-scalpel` (e.g., `test/playground/`) or a standalone `o2-scalpel-playground` repo? A standalone repo more faithfully represents "real user experience" but adds repo management overhead.
2. **URL to exercise.** Should the playground test the published `git+https://github.com/o2services/o2-scalpel.git#subdirectory=vendor/serena` URL, or a pinned `@<tag>` ref? Unpinned main-branch tests are noisy; pinned-ref tests require bumping on every release.
3. **What counts as a passing smoke?** Options: (a) `tools/list` returns expected tool names, (b) additionally call one real tool against a fixture project, (c) additionally run `cargo test` byte-identical after a split. Level (c) requires `rust-analyzer` + `cargo` on the CI runner.
4. **`verify-scalpel-rust.sh` scope.** Should the hook be upgraded to do a full MCP-boot smoke, or keep it PATH-only and let the playground cover the deeper check?
5. **Frequency.** Should playground CI run on every push to `o2-scalpel` main, or on a nightly schedule (since it requires network + LSP binary install)?
6. **`o2services` org URL.** The `.mcp.json` references `github.com/o2services/o2-scalpel` but the actual repo is at `github.com/o2alexanderfedin/o2-scalpel`. This URL discrepancy needs resolution before any playground test of the published path can pass.
