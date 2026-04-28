---
name: using-scalpel-inline-go
description: When user asks to inline a function at all call sites in Go, use scalpel_inline
type: skill
---

# Scalpel - inline (Go)

Inline a function at all call sites

## When to use

Invoke `scalpel_inline` (language: **go**) when the user says any of:

- "inline this"
- "inline function"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.inline]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_inline", "arguments": {"path": "<file>", "language": "go"}}
```
