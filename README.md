# o2.scalpel

LSP-driven semantic refactoring for agentic AI clients via the Model Context Protocol.

## Status

Design phase. Implementation has not started in this iteration. The complete design report and all supporting research live under [`docs/`](docs/).

## What it is

A Claude Code plugin that exposes write/refactor operations from any installed Language Server Protocol server as MCP tools, complementing Claude Code's built-in (read-only) `LSP` umbrella tool.

- **Read** comes from Claude Code itself: `definition`, `references`, `hover`, `documentSymbol`, `callHierarchy`.
- **Write** comes from o2.scalpel: `codeAction`, `codeAction/resolve`, `applyEdit`, `rename`, `executeCommand`, plus task-level facades (`split_file_by_symbols`, `extract_symbols_to_module`, `fix_imports`, `rollback_refactor`).

Built on top of the [Serena](https://github.com/oraios/serena) MCP server, extended with a language-agnostic facade layer and per-language `LanguageStrategy` plugins. Rust is the v1 strategy.

## Layout

```
.
├── docs/
│   ├── design/      Authoritative design reports
│   └── research/    Specialist briefs that fed the design
└── vendor/
    ├── serena/                          Fork of oraios/serena (MIT) — extension target
    ├── claude-code-lsps-boostvolt/      Fork of boostvolt/claude-code-lsps (MIT) — analysis only
    └── claude-code-lsps-piebald/        Fork of Piebald-AI/claude-code-lsps (no LICENSE) — private analysis only, never redistributed
```

## Where to start

1. [Design report — Serena rust-analyzer refactoring extensions](docs/design/2026-04-24-serena-rust-refactoring-extensions-design.md)
2. [Open-questions resolution — cache, marketplace, two-process, fork legality, generator](docs/design/2026-04-24-o2-scalpel-open-questions-resolution.md)
3. [Research briefs](docs/research/) — eight parallel-agent specialist outputs that fed the design

## Origin

Spun out of `hupyy/hupyy-cpp-to-rust` on 2026-04-24 once it became clear the LSP-write capability is a general-purpose agentic-AI tool, not coupled to any specific transpiler project.

## License

To be determined for original code in this repo. Forks under `vendor/` retain their upstream licenses (Serena: MIT, boostvolt: MIT, Piebald: not redistributable).
