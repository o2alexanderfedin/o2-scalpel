# Changelog

All notable changes to o2.scalpel are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### v1.4.1 — SMT2 dolmenls upgrade (Stream 6 follow-up)

- Lifted `o2-scalpel-smt2` from stub to fully-wired LSP-backed plugin via [dolmenls](https://github.com/Gbury/dolmen) (the Dolmen monorepo's diagnostics-focused SMT-LIB language server, pinned to v0.10).
- Architectural decision: GitHub-Releases binary download (chosen over an opam channel) per `docs/superpowers/plans/2026-04-28-v1-4-1-smt2-dolmenls/README.md` §"install channel". KISS / user-side simplicity — most users have no OCaml toolchain; pre-built ~13–21 MB asset lands at `~/.local/bin/dolmenls`.
- New `Smt2Installer` (~250 LoC + 22 tests) following the existing `LspInstaller` ABC; uses a single `("sh", "-c", "<chain>")` invocation that does `mkdir -p && curl -fL && chmod +x`. Auditable verbatim via the dry-run envelope; safety gate (`allow_install=False` default) preserved.
- Capability surface stays diagnostics-only in the static catalog; runtime `DynamicCapabilityRegistry` (v0.2.0-followup-01) gates per-method support honestly per session — facades not advertised by dolmenls return `CAPABILITY_NOT_AVAILABLE` envelopes.
- Pre-existing FAILs surfaced en route + fixed atomically per "all errors must be fixed":
  - `fix(ansible)`: honest-skip hover/completion when `ansible-lint` missing.
  - `fix(test)`: stale `marketplace.json` path post-v1.2.2 relocation (`<repo>/marketplace.json` → `<repo>/.claude-plugin/marketplace.json`).
- Submodule tag: `v1.4.1-smt2-dolmenls-complete` (`93bf70a8`); parent tag follows in this release block.

### Type-error coverage

- **pylsp-mypy enabled** with `live_mode: false` + `dmypy: true` per P5a outcome B (stale_rate 0.00%, p95 2.668s on re-run). Expect occasional latency >1s on first didSave after long idle while the dmypy daemon warms; subsequent didSaves complete in ~1.25s. Reconciles `docs/superpowers/plans/spike-results/PROGRESS.md` decision-log §70.

### Documentation hygiene (post-v0.2.0 review batch — no tag yet)

- Refreshed `CHANGELOG.md` (this file) with the seven shipped tags between v0.1.0 and `stage-v0.2.0-followups-complete` that had not yet been recorded.
- Updated `docs/superpowers/plans/2026-04-24-mvp-execution-index.md` status column so stages 1A, 1B, 1H, 1I, 2A, 2B reflect their shipped tags rather than "Plan ready".
- Added a stale-numbers banner to `docs/design/mvp/2026-04-24-mvp-scope-report.md` (headline says 13 + 11 = 24; reality at `stage-v0.2.0-followups-complete` is 8 primitives + 25 facades = 33 always-on tools).
- Added a Stream 3 COMPLETE banner to `docs/superpowers/plans/2026-04-26-INDEX-post-v0.3.0.md` referencing tag `stage-v0.2.0-followups-complete`.
- Added a "Plan File Conventions" rule to `CLAUDE.md`: atomic plan files must carry a STATUS update by day-N+7; TREE plans are exempt because their leaf table is the status tracker.

## [0.3.0-facade-application] — 2026-04-26

- Stage 3 facade-application gap CLOSED: pure-python `WorkspaceEdit` applier wired into all 8 facade dispatch sites so facades that previously discovered edits but did not write them now actually mutate the workspace. Spike-suite 696 passing (+8); E2E 20 passing (+2 SKIP→PASS). Six pre-existing `inspect.getsource` flakes documented (not regression).
- Tag covers parent `feature/v030-facade-application` merge into `main`; submodule pointer updated.

## [0.2.0-stage-3-complete] — 2026-04-26

- Stage 3 T1–T9 fully landed: 25 ergonomic facades + 8 always-on primitives + 8 long-tail E2E scenarios + README/install docs.
- Documents the v0.3.0 facade-application architectural gap (facades discover but do not write — the Stage 2A pattern was inherited and is closed by the v0.3.0 tag above).

## [0.2.0-stage-3-facades-complete] — 2026-04-26

- Twelve Rust + eight Python ergonomic facades + the T8 server-extension whitelist landed; spike-suite 680 passing (+66 tests).
- E13-py dedup gap CLOSED via `scalpel_fix_lints` (`source.fixAll.ruff`). Stage 3 T6/T7/T9 deferred to the parent v0.2.0-stage-3-complete tag.

## [0.2.0-critical-path] — 2026-04-26

- Seven backlog items from the v0.2.0 critical path landed alongside the Stage 1H flake fix; spike-suite 614/3 skips, E2E 18 passing / 9 skips / 1 FAIL.
- E13-py dedup gap surfaces honestly in this tag and is closed in `v0.2.0-stage-3-facades-complete` above.

## [0.1.0-mvp] — 2026-04-26

- MVP cut: Stages 1H-min + 1I + 2A + 2B all landed at parent main `87a5617`, submodule main `229a46d5`.
- Spike-suite 590/3 skips + E2E 18/10 skips; Stage 1 gate green; six MVP-cut axes met.
- Nine E2E scenarios partially green (0 FAIL; skips trace to host-cargo and LSP-startup gaps documented separately).

### Submodule-only milestone (recorded for traceability)

## [stage-v0.2.0-followup-01-basedpyright-dynamic-capability-complete] — 2026-04-26 (submodule tag)

- basedpyright dynamic-capability gap CLOSED: `DynamicCapabilityRegistry` + `LanguageHealth.dynamic_capabilities` tuple + base `_handle_register_capability` extension + `ClassVar server_id` (basedpyright + pylsp wired); 8 new tests; 0/0/0 pyright. Catalog-evolution caveat documented.
- This tag lives only in `vendor/serena`; the parent repo records it through the submodule pointer landed in `stage-v0.2.0-followups-complete`.

## [stage-v0.2.0-followups-complete] — 2026-04-27

- v0.2.0 follow-ups complete: leaves 02, 03, 04, 05 of the `2026-04-26-v020-followups` TREE landed (plus the basedpyright dynamic-capability submodule work captured above).

## [0.1.0] — 2026-04-24

Initial repository carved out of `hupyy/hupyy-cpp-to-rust`. Design-only release; no implementation yet.

### Added
- `docs/design/2026-04-24-serena-rust-refactoring-extensions-design.md` — authoritative design report covering primitives, agnostic facades, `LanguageStrategy` interface, Claude Code plugin deployment, fixture crate (`calcrs`), test strategy including 10 E2E scenarios, and 14 resolved open questions.
- `docs/design/2026-04-24-o2-scalpel-open-questions-resolution.md` — focused resolution doc for Q10–Q14 (cache discovery + lazy spawn, marketplace location, two-LSP-process cost, fork legality, on-demand template-generator).
- `docs/research/` — ten specialist briefs feeding the design (Serena architecture, rust-analyzer capabilities, MCP/LSP protocol mechanics, DX/facade design, boostvolt audit, plugin extension surface, cache/lazy-spawn research, marketplace, two-process problem, license/rename feasibility).
- `vendor/serena/` — submodule pointing at `o2alexanderfedin/serena` (MIT, fork of oraios/serena).
- `vendor/claude-code-lsps-boostvolt/` — submodule pointing at fork of `boostvolt/claude-code-lsps` (MIT, analysis-only).
- `vendor/claude-code-lsps-piebald/` — submodule pointing at fork of `Piebald-AI/claude-code-lsps` (no LICENSE; private analysis-only, must NOT be redistributed in releases).

### Notes
- All commits prior to this repository's creation live in the upstream `hupyy/hupyy-cpp-to-rust` history, tags `2.7.1` through `2.7.4`. See those release notes for the design's evolution.
