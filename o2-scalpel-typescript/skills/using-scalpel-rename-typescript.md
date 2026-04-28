---
name: using-scalpel-rename-typescript
description: When user asks to rename a symbol across the workspace in TypeScript, use scalpel_rename
type: skill
---

# Scalpel - rename (TypeScript)

Rename a symbol across the workspace

## When to use

Invoke `scalpel_rename` (language: **typescript**) when the user says any of:

- "rename this"
- "refactor name"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "scalpel_rename", "arguments": {"path": "<file>", "language": "typescript"}}
```
