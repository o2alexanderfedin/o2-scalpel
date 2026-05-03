---
name: using-fix-lints-kotlin
description: When user asks to apply lsp diagnostic quick-fixes in Kotlin, use fix_lints
type: skill
---

# Scalpel - fix_lints (Kotlin)

Apply LSP diagnostic quick-fixes

## When to use

Invoke `fix_lints` (language: **kotlin**) when the user says any of:

- "fix lints"
- "apply quickfixes"

> v2.0 wire-name cleanup: the legacy alias `scalpel_fix_lints` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "fix_lints", "arguments": {"path": "<file>", "language": "kotlin"}}
```
