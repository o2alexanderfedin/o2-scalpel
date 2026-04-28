---
name: using-scalpel-rename-predicate-prolog
description: When user asks to rename a prolog predicate or variable across the current file in Prolog (SWI-Prolog), use scalpel_rename_predicate
type: skill
---

# Scalpel - rename_predicate (Prolog (SWI-Prolog))

Rename a Prolog predicate or variable across the current file

## When to use

Invoke `scalpel_rename_predicate` (language: **prolog**) when the user says any of:

- "rename"
- "rename predicate"
- "rename variable"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_rename_predicate", "arguments": {"path": "<file>", "language": "prolog"}}
```
