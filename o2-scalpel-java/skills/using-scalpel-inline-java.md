---
name: using-scalpel-inline-java
description: When user asks to inline a local variable or method at all call sites in Java, use scalpel_inline
type: skill
---

# Scalpel - inline (Java)

Inline a local variable or method at all call sites

## When to use

Invoke `scalpel_inline` (language: **java**) when the user says any of:

- "inline this"
- "inline variable"
- "inline method"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.inline]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_inline", "arguments": {"path": "<file>", "language": "java"}}
```
