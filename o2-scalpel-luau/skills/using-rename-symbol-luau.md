---
name: using-rename-symbol-luau
description: When user asks to rename a symbol across the workspace in Luau, use rename_symbol
type: skill
---

# Scalpel - rename_symbol (Luau)

Rename a symbol across the workspace

## When to use

Invoke `rename_symbol` (language: **luau**) when the user says any of:

- "rename this"
- "refactor name"

> v2.0 wire-name cleanup: the legacy alias `scalpel_rename_symbol` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "rename_symbol", "arguments": {"path": "<file>", "language": "luau"}}
```
