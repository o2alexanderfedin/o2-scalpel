# v1.4.1 — SMT2 dolmenls upgrade (Stream 6 follow-up)

**Status:** COMPLETE — submodule tag `v1.4.1-smt2-dolmenls-complete` (`93bf70a8`)
**Author:** AI Hive®
**Date:** 2026-04-28
**Parent milestone:** v1.4 (Stream 6 polyglot — `v1.4-stream6-polyglot-complete`)

## Goal

Lift the `o2-scalpel-smt2` plugin from **stub** to **real LSP-backed** by wiring it
to [`dolmenls`](https://github.com/Gbury/dolmen) — the Dolmen-based SMT-LIB language
server. The seam already exists (adapter, strategy, installer-stub, language enum,
11 unit tests); this milestone fills it in.

## Why now

- The v1.4 SMT2 stub was conditional on no production SMT2 LSP existing. **dolmenls
  exists**, ships pre-built binaries on GitHub Releases (v0.10), and is actively
  maintained on master through 2026-03-16.
- The previous-session author left an explicit upgrade checklist in
  `vendor/serena/src/serena/installer/smt2_installer.py:49–57` — this is exactly
  the work below.
- Strategic end-goal memory: "Claude CLI uses LSPs at full extent for search /
  navigate / edit on code AND markdown" — SMT2 was the last stub in Stream 6.

## Architectural decision: install channel

Three options were considered:

| Option | Pros | Cons | Decision |
|---|---|---|---|
| **opam** (`opam install dolmen_lsp`) | Official upstream channel; reusable for future OCaml-ecosystem LSPs (Alt-Ergo, OCaml-LSP itself) | Adds 5th install channel; heavy host dep (OCaml toolchain); slow first install (compiles from source); most users don't have opam | rejected |
| **GitHub-Releases binary download** | Pre-built ~13–21 MB; fast install; no host deps; pinned versioning; matches `dolmenls-{linux,macos,windows}-amd64` asset shape | New pattern in this codebase (current installers use brew/cargo/pipx/npm/elan) | **chosen** |
| Hybrid (opam-first, fallback to download) | Maximally robust | Doubles installer complexity for marginal gain | rejected |

**Rationale:** KISS + user-side simplicity. Most o2-scalpel users have no OCaml
toolchain; opam would force a heavy install for a single SMT2 binary. The
GitHub-Releases pattern slots into the existing `LspInstaller` ABC without
introducing a 5th package-manager channel.

**Pin:** `v0.10` (latest release as of 2026-04-28). Pin-bump policy: same as Lean
(manual update on quarterly cadence; CI drift check would surface staleness).

## Capability surface

dolmenls is **diagnostics-only** in practice (per upstream `doc/lsp.md` and the
`hra687261/smt-lsp-vscode-extension` reference): `textDocument/publishDiagnostics`
is the headline feature. Hover / goto-def / references / documentSymbol /
formatting / rename / codeAction are not implemented today.

The existing v0.2.0-followup-01 `DynamicCapabilityRegistry` machinery handles
this honestly: the adapter advertises a wide capability set (already wired);
`ServerCapabilities` from the initialize response gates per-method support at
runtime. Facades that aren't supported return `CAPABILITY_NOT_AVAILABLE` envelopes
— consistent with the post-v0.2.0 "honest-skip" pattern.

## Leaf table

| Leaf | Subject | LoC actual | Risk | Status |
|---|---|---|---|---|
| A | Smt2Server adapter binary + generator update | 140 | low — direct rename | COMPLETE (`bfd76d12`) |
| B | Smt2Installer fill-in (GitHub-Releases downloader) | 574 | medium — new install pattern | COMPLETE (`75dde8f1`) |
| C | Capability catalog baseline refresh | 1 | low — `--update-catalog-baseline` | COMPLETE (`f33a8d40`) |
| D | Integration smoke + honest-skip gating | 81 | low — mirrors `test_marksman_smoke` | COMPLETE (`d40b2bd2`) |
| E | Docs + CHANGELOG + tag v1.4.1 + plugin regen | (this commit) | trivial | COMPLETE |

**Pre-existing bugs surfaced en route + fixed atomically (per "all errors must be fixed" autonomy directive):**

| SHA | Type | Subject |
|---|---|---|
| `76b192b3` | fix(ansible) | honest-skip hover/completion when ansible-lint missing |
| `dbac4993` | fix(test) | stale marketplace.json path post-v1.2.2 relocation |

Total submodule diff: ~711 insertions / ~179 deletions.

**Note on Leaf C scope adjustment:** Original plan bundled plugin tree regen + capability baseline + marketplace into Leaf C. In execution, plugin tree regeneration was deferred to Leaf E (the parent commit) because banner SHA stamping requires the final submodule pointer SHA. Leaf C trimmed to just the catalog baseline.

## Per-leaf detail

### Leaf A — adapter binary + generator update

**Files:**
- `vendor/serena/src/solidlsp/language_servers/smt2_server.py`
  - `_SMT2_LSP_BINARY = "smt2-lsp"` → `"dolmenls"`
  - `cmd=f"{binary} --stdio"` → `cmd=binary` (dolmenls is bare)
  - `server_id = "smt2-lsp"` → `"dolmenls"`
  - Drop the "stub / no production LSP" prose from the docstring; keep the
    diagnostics-only justification
- `vendor/serena/src/serena/refactoring/cli_newplugin.py`
  - SMT2 `_StrategyView`: `lsp_server_cmd = ("smt2-lsp", "--stdio")` →
    `("dolmenls",)`
- `vendor/serena/test/solidlsp/test_smt2_server.py`
  - 11 tests: update assertions to expect `"dolmenls"` binary + `server_id`

**TDD:** update tests first (red), then code (green), submodule pyright 0/0/0,
atomic submodule commit.

### Leaf B — Smt2Installer fill-in

**File:** `vendor/serena/src/serena/installer/smt2_installer.py`

Replace `NotImplementedError` with a GitHub-Releases binary downloader:

```python
class Smt2Installer(LspInstaller):
    language = "smt2"
    binary_name = "dolmenls"
    _PINNED_VERSION = "v0.10"
    _RELEASE_BASE = "https://github.com/Gbury/dolmen/releases/download"

    def detect_installed(self) -> InstalledStatus:
        # shutil.which + best-effort version probe (--version may not exist;
        # fall back to file mtime or release-pin string)

    def latest_available(self) -> str | None:
        # Query https://api.github.com/repos/Gbury/dolmen/releases/latest
        # 5s timeout, return None on network/parse failure (offline-safe)

    def _install_command(self) -> tuple[str, ...]:
        # Platform-aware asset name: dolmenls-{linux,macos,windows}-amd64
        # Returns argv tuple — actual download happens in install() via
        # urllib (mirrors existing subprocess discipline; no curl dep)
```

**Tests:** `vendor/serena/test/serena/installer/test_smt2_installer.py`
- `detect_installed` when binary present / absent (mock `shutil.which`)
- `latest_available` parses GitHub API JSON; returns `None` on offline
- Platform branching for asset name selection
- `dry_run=True` default — no real download
- `allow_install=True` actually downloads + chmods (mocked subprocess + urllib)

### Leaf C — plugin regen + marketplace + capabilities

**Files:**
- `o2-scalpel-smt2/.mcp.json` — regenerated from updated `cli_newplugin.py`
- `o2-scalpel-smt2/.claude-plugin/plugin.json` — regenerated
- `o2-scalpel-smt2/README.md` — regenerated; drop stub language
- `o2-scalpel-smt2/skills/using-scalpel-fix-lints-smt2.md` — regenerated
- `o2-scalpel-smt2/hooks/verify-scalpel-smt2.sh` — checks `dolmenls` on PATH
- `marketplace.surface.json` — add SMT2 entry with install_hint
- `vendor/serena/src/serena/refactoring/capabilities.py` — add
  `_DEFAULT_SOURCE_SERVER_BY_LANGUAGE["smt2"] = "dolmenls"`
- Refresh capability catalog baseline: `pytest --update-catalog-baseline`

### Leaf D — integration smoke + honest-skip gating

**File:** `vendor/serena/test/integration/test_dolmenls_smoke.py`

```python
@pytest.mark.skipif(
    shutil.which("dolmenls") is None,
    reason="dolmenls binary not on PATH (install via scalpel_install_lsp_servers)",
)
def test_dolmenls_diagnostics_round_trip(tmp_path: Path) -> None:
    # Write tiny .smt2 fixture
    # Boot Smt2Server
    # Wait for publishDiagnostics
    # Assert no parse errors on valid input
    # Assert at least one diagnostic on a deliberately-bad fixture
```

Confirm full suite still passes: 614+/3 skip → 615+/3 skip + 1 dolmenls skip
(unless host has dolmenls installed via Leaf B's installer, in which case the
smoke test PASSes).

### Leaf E — docs + CHANGELOG + tag

- `o2-scalpel-smt2/README.md` provenance banner
- `CHANGELOG.md` — v1.4.1 entry summarizing dolmenls wiring
- This plan's `README.md` STATUS column → COMPLETED for each leaf
- Memory file: `project_v1_4_1_smt2_dolmenls_complete.md`
- Tag: `v1.4.1-smt2-dolmenls-complete` (parent + submodule bump)

## Out of scope

- Adding opam as a 5th installer channel (deferred to a future OCaml-ecosystem
  milestone — Alt-Ergo, OCaml-LSP, etc., would justify it)
- Dolmen-aware refactoring facades (rename / extract). Dolmen does not expose
  these via LSP today; the current strategy correctly advertises only `quickfix`.
- Solver integration (Z3/CVC5 shell-out for `(check-sat)` diagnostics). Dolmenls
  handles syntactic + sort-level diagnostics; solver-level satisfiability checking
  is a future facade.

## Risk + rollback

- **Risk: dolmenls v0.10 binary fails on host platform.**
  Mitigation: installer dry_run=True default; user opt-in via allow_install.
  Rollback: revert installer to NotImplementedError stub; adapter still works
  if user installs dolmenls manually via opam.

- **Risk: capability catalog drift CI fails after baseline refresh.**
  Mitigation: regenerate baseline as part of Leaf C; CI check should pass on
  the freshly-refreshed baseline.

- **Risk: existing 11 unit tests break in unexpected ways from binary rename.**
  Mitigation: Leaf A is TDD-first; tests are updated before code.

## Verification gate (definition of done)

1. Submodule `pyright` 0 errors / 0 warnings / 0 hints.
2. Submodule full test suite ≥614 PASS / 3 SKIP (no new FAILs; +N for new
   installer + smoke tests).
3. Capability catalog drift CI green.
4. `o2-scalpel-smt2` plugin loads without verify-script error when dolmenls is
   installed; exits cleanly with guidance when not.
5. Tag `v1.4.1-smt2-dolmenls-complete` on parent + submodule bump committed.
