---
name: using-scalpel-fix-lints-problog
description: When user asks to apply diagnostic quick-fixes (singleton variables, syntax errors) in ProbLog, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (ProbLog)

Apply diagnostic quick-fixes (singleton variables, syntax errors)

## When to use

Invoke `scalpel_fix_lints` (language: **problog**) when the user says any of:

- "fix all"
- "fix lints"
- "fix syntax"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "problog"}}
```
