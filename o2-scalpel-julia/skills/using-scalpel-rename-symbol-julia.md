---
name: using-scalpel-rename-symbol-julia
description: When user asks to rename a symbol across the workspace in Julia, use scalpel_rename_symbol
type: skill
---

# Scalpel - rename_symbol (Julia)

Rename a symbol across the workspace

## When to use

Invoke `scalpel_rename_symbol` (language: **julia**) when the user says any of:

- "rename this"
- "refactor name"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "scalpel_rename_symbol", "arguments": {"path": "<file>", "language": "julia"}}
```
