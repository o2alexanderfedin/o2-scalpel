---
name: using-rename-predicate-prolog
description: When user asks to rename a prolog predicate or variable across the current file in Prolog (SWI-Prolog), use rename_predicate
type: skill
---

# Scalpel - rename_predicate (Prolog (SWI-Prolog))

Rename a Prolog predicate or variable across the current file

## When to use

Invoke `rename_predicate` (language: **prolog**) when the user says any of:

- "rename"
- "rename predicate"
- "rename variable"

> v2.0 wire-name cleanup: the legacy alias `scalpel_rename_predicate` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "rename_predicate", "arguments": {"path": "<file>", "language": "prolog"}}
```
