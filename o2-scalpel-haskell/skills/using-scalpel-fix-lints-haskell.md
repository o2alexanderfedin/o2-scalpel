---
name: using-scalpel-fix-lints-haskell
description: When user asks to apply hlint + retrie diagnostic quick-fixes in Haskell, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (Haskell)

Apply hlint + retrie diagnostic quick-fixes

## When to use

Invoke `scalpel_fix_lints` (language: **haskell**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "haskell"}}
```
