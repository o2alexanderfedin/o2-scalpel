---
name: using-fix-lints-lean
description: When user asks to apply tactic suggestions and auto-fixable diagnostics (quickfix) in Lean 4, use fix_lints
type: skill
---

# Scalpel - fix_lints (Lean 4)

Apply tactic suggestions and auto-fixable diagnostics (quickfix)

## When to use

Invoke `fix_lints` (language: **lean**) when the user says any of:

- "fix all"
- "fix lints"
- "apply tactic"
- "try this"

> v2.0 wire-name cleanup: the legacy alias `scalpel_fix_lints` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "fix_lints", "arguments": {"path": "<file>", "language": "lean"}}
```
