---
name: using-scalpel-rename-java
description: When user asks to rename a symbol across the workspace in Java, use scalpel_rename
type: skill
---

# Scalpel - rename (Java)

Rename a symbol across the workspace

## When to use

Invoke `scalpel_rename` (language: **java**) when the user says any of:

- "rename this"
- "refactor name"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "scalpel_rename", "arguments": {"path": "<file>", "language": "java"}}
```
