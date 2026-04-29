---
name: using-scalpel-fix-lints-csharp
description: When user asks to apply all auto-fixable diagnostics (quickfix) in C#, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (C#)

Apply all auto-fixable diagnostics (quickfix)

## When to use

Invoke `scalpel_fix_lints` (language: **csharp**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "csharp"}}
```
