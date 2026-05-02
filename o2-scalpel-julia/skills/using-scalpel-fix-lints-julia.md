---
name: using-scalpel-fix-lints-julia
description: When user asks to apply lsp diagnostic quick-fixes in Julia, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (Julia)

Apply LSP diagnostic quick-fixes

## When to use

Invoke `scalpel_fix_lints` (language: **julia**) when the user says any of:

- "fix lints"
- "apply quickfixes"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "julia"}}
```
