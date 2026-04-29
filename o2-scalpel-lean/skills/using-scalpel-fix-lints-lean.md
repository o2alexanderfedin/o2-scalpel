---
name: using-scalpel-fix-lints-lean
description: When user asks to apply tactic suggestions and auto-fixable diagnostics (quickfix) in Lean 4, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (Lean 4)

Apply tactic suggestions and auto-fixable diagnostics (quickfix)

## When to use

Invoke `scalpel_fix_lints` (language: **lean**) when the user says any of:

- "fix all"
- "fix lints"
- "apply tactic"
- "try this"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "lean"}}
```
