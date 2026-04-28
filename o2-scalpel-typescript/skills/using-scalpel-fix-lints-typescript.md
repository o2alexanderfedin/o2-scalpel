---
name: using-scalpel-fix-lints-typescript
description: When user asks to apply all auto-fixable diagnostics (source.fixall) in TypeScript, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (TypeScript)

Apply all auto-fixable diagnostics (source.fixAll)

## When to use

Invoke `scalpel_fix_lints` (language: **typescript**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.fixAll]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "typescript"}}
```
