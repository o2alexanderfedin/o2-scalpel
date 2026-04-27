# Changelog

All notable changes to o2.scalpel are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Type-error coverage

- **pylsp-mypy enabled** with `live_mode: false` + `dmypy: true` per P5a outcome B (stale_rate 0.00%, p95 2.668s on re-run). Expect occasional latency >1s on first didSave after long idle while the dmypy daemon warms; subsequent didSaves complete in ~1.25s. Reconciles `docs/superpowers/plans/spike-results/PROGRESS.md` decision-log §70.

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
