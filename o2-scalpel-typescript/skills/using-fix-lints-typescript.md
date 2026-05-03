---
name: using-fix-lints-typescript
description: When user asks to apply all auto-fixable diagnostics (source.fixall) in TypeScript, use fix_lints
type: skill
---

# Scalpel - fix_lints (TypeScript)

Apply all auto-fixable diagnostics (source.fixAll)

## When to use

Invoke `fix_lints` (language: **typescript**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

> v2.0 wire-name cleanup: the legacy alias `scalpel_fix_lints` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.fixAll]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "fix_lints", "arguments": {"path": "<file>", "language": "typescript"}}
```
