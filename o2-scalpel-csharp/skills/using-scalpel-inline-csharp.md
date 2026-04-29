---
name: using-scalpel-inline-csharp
description: When user asks to inline a method at all call sites in C#, use scalpel_inline
type: skill
---

# Scalpel - inline (C#)

Inline a method at all call sites

## When to use

Invoke `scalpel_inline` (language: **csharp**) when the user says any of:

- "inline this"
- "inline method"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.inline]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_inline", "arguments": {"path": "<file>", "language": "csharp"}}
```
