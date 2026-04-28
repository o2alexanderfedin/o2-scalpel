---
name: using-scalpel-inline-cpp
description: When user asks to inline a function at all call sites in C/C++, use scalpel_inline
type: skill
---

# Scalpel - inline (C/C++)

Inline a function at all call sites

## When to use

Invoke `scalpel_inline` (language: **cpp**) when the user says any of:

- "inline this"
- "inline function"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.inline]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_inline", "arguments": {"path": "<file>", "language": "cpp"}}
```
