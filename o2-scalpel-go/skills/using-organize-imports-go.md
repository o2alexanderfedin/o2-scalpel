---
name: using-organize-imports-go
description: When user asks to remove unused imports and sort import order in Go, use organize_imports
type: skill
---

# Scalpel - organize_imports (Go)

Remove unused imports and sort import order

## When to use

Invoke `organize_imports` (language: **go**) when the user says any of:

- "organize imports"
- "sort imports"
- "clean imports"

> v2.0 wire-name cleanup: the legacy alias `scalpel_organize_imports` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.organizeImports]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "organize_imports", "arguments": {"path": "<file>", "language": "go"}}
```
