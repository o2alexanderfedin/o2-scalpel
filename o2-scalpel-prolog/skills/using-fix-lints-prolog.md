---
name: using-fix-lints-prolog
description: When user asks to apply diagnostic quick-fixes (singleton variables, syntax errors) in Prolog (SWI-Prolog), use fix_lints
type: skill
---

# Scalpel - fix_lints (Prolog (SWI-Prolog))

Apply diagnostic quick-fixes (singleton variables, syntax errors)

## When to use

Invoke `fix_lints` (language: **prolog**) when the user says any of:

- "fix all"
- "fix lints"
- "fix singleton"

> v2.0 wire-name cleanup: the legacy alias `scalpel_fix_lints` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "fix_lints", "arguments": {"path": "<file>", "language": "prolog"}}
```
