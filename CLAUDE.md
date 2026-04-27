# Claude Code Guidelines for o2.scalpel

## Project Context

o2.scalpel is a Claude Code plugin that exposes LSP write/refactor operations as MCP tools. It bundles an MCP server built on a fork of [Serena](https://github.com/oraios/serena), extended with language-agnostic facades and per-language `LanguageStrategy` plugins.

The authoritative design lives at `docs/design/`. Read those before proposing architecture changes.

## Task Execution Strategy

### Context Optimization
Extensively use tasks and subtasks (Task tool) to optimize context usage.

### Parallel Execution
Run independent subtasks in parallel (multiple Task tools in a single message). Coordinate carefully to avoid file conflicts; use map/reduce when work touches independent files.

### Map-Reduce Approach
Parallelize work that touches independent files/modules, then use a single subagent to merge results or do anything requiring exclusive access.

### Task Reporting
Each task or subtask reports a brief explanation of what was done and what still needs to be done.

### Problem Resolution
When a task experiences a problem, spawn additional subtask(s) to research/experiment toward a resolution.

### Planning and Tracking
Extensively use TodoWrite so all work is tracked and nothing is skipped.

### Parallelization Limits
Maximum parallel tasks must not exceed CPU cores on this machine.

## Mandatory Principles
- SOLID
- KISS
- DRY
- YAGNI
- TRIZ — when facing constraints, identify contradictions and apply segmentation/separation principles; look for existing patterns to adapt before inventing.

## Development Process

### TDD (Test-Driven Development)
1. Write failing test first
2. Write minimal code to pass
3. Refactor while keeping tests green

### Testing Requirements
Both unit and integration tests. End-to-end tests as specified in the design report's §End-to-end tests.

### Type Safety
Write code as strongly typed as the language allows. For Python: full type hints + `pydantic` for schema-validated boundaries.

### Linting
Run applicable linters exhaustively before pushing.

### Code Review
Review changes with a separate subtask before commit.

## Naming Conventions
- Prefer clear explanatory names over jargon or abbreviations.
- Names should explain WHAT the code does, not use domain-specific terminology.
- If domain terms are unavoidable, document them.

## Documentation

### Single Source of Truth
Each piece of information has one canonical location. Never duplicate across files. Link to the canonical source instead.

### Plan File Conventions

- **Atomic plan files** (single-file plans like `decision-*.md` or `fix-*.md`) drafted on day-N must have a STATUS update by day-N+7 (executed, deferred, or superseded). TREE plans (multi-leaf with `README.md` + leaf table) have built-in per-leaf cadence and are exempt — their leaf table IS the status tracker.

## Git Workflow

### Git Flow
Use git flow for all git/github actions.

### No Pull Requests
Solo development.

### Commit and Push
Commit and push after every engineering task.

### Releases
Tag a release after each significant feature or piece is implemented.

## Time
**Never estimate time** unless explicitly asked. Effort is sized via small/medium/large or LoC counts.

## Author
AI Hive(R). Never use "Claude" as the author identifier in commits.

---
**Last Updated**: 2026-04-27
**Spun out of**: `hupyy/hupyy-cpp-to-rust`
