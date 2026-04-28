---
name: using-scalpel-inline-typescript
description: When user asks to inline a local variable or function at all call sites in TypeScript, use scalpel_inline
type: skill
---

# Scalpel - inline (TypeScript)

Inline a local variable or function at all call sites

## When to use

Invoke `scalpel_inline` (language: **typescript**) when the user says any of:

- "inline this"
- "inline variable"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.inline]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_inline", "arguments": {"path": "<file>", "language": "typescript"}}
```
