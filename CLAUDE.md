# Claude Code Guidelines for o2.scalpel

## Project Context

o2.scalpel is a Claude Code plugin that exposes LSP write/refactor operations as MCP tools. The MCP engine (o2-scalpel-engine, forked from [Serena](https://github.com/oraios/serena)) is extended with language-agnostic facades and per-language `LanguageStrategy` plugins.

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

## Tool routing (Scalpel facades vs Serena upstream primitives)

The MCP engine vendored at `vendor/serena/` exposes two tool families to the LLM:

1. **Scalpel facades** — `scalpel_*` tools (e.g. `scalpel_extract`, `scalpel_rename`, `scalpel_split_file`, `scalpel_fix_lints`, `scalpel_organize_imports`, `scalpel_inline`, `scalpel_extract_section`). Their docstring opens with `PREFERRED:`. These are the **first-line surface** for refactor / rename / extract / inline / split / organize-imports / fix-lints work.
2. **Serena upstream primitives** — `find_symbol`, `replace_symbol_body`, `insert_after_symbol`, `insert_before_symbol`, `safe_delete_symbol`, `search_for_pattern`, `find_referencing_symbols`, `get_symbols_overview`, `read_file`. Their docstrings do NOT open with `PREFERRED:` — that absence is the AST-fallback signal.

**Routing rule:** for any refactor / rename / extract / inline / split / organize-imports / fix-lints task, reach for the matching `scalpel_*` facade FIRST. Only fall back to Serena primitives when (a) the facade returns `CAPABILITY_NOT_AVAILABLE`, (b) no facade exists for the operation, or (c) you need raw symbol-level navigation (find a definition, list a file's symbols).

The `PREFERRED:` / `FALLBACK:` opener convention is enforced by drift-CI at `vendor/serena/test/serena/tools/test_docstring_convention.py`. The authoritative spec is `docs/superpowers/specs/2026-04-29-lsp-feature-coverage-spec.md` §5.

---
**Last Updated**: 2026-05-01
**Spun out of**: `hupyy/hupyy-cpp-to-rust`

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
