---
name: using-scalpel-rewrite-csharp
description: When user asks to apply rewrite transformations (convert, invert, etc.) in C#, use scalpel_rewrite
type: skill
---

# Scalpel - rewrite (C#)

Apply rewrite transformations (convert, invert, etc.)

## When to use

Invoke `scalpel_rewrite` (language: **csharp**) when the user says any of:

- "rewrite this"
- "convert to"
- "invert condition"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.rewrite]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_rewrite", "arguments": {"path": "<file>", "language": "csharp"}}
```
