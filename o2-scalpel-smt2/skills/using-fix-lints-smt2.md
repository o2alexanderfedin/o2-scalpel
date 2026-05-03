---
name: using-fix-lints-smt2
description: When user asks to apply diagnostic quick-fixes (sort mismatch, syntax errors) in SMT-LIB 2, use fix_lints
type: skill
---

# Scalpel - fix_lints (SMT-LIB 2)

Apply diagnostic quick-fixes (sort mismatch, syntax errors)

## When to use

Invoke `fix_lints` (language: **smt2**) when the user says any of:

- "fix all"
- "fix lints"
- "fix syntax"

> v2.0 wire-name cleanup: the legacy alias `scalpel_fix_lints` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "fix_lints", "arguments": {"path": "<file>", "language": "smt2"}}
```
