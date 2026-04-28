---
name: using-scalpel-rename-cpp
description: When user asks to rename a symbol across the workspace in C/C++, use scalpel_rename
type: skill
---

# Scalpel - rename (C/C++)

Rename a symbol across the workspace

## When to use

Invoke `scalpel_rename` (language: **cpp**) when the user says any of:

- "rename this"
- "refactor name"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "scalpel_rename", "arguments": {"path": "<file>", "language": "cpp"}}
```
