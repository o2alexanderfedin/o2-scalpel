---
name: using-scalpel-fix-lints-cpp
description: When user asks to apply all auto-fixable diagnostics (source.fixall.clangd) in C/C++, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (C/C++)

Apply all auto-fixable diagnostics (source.fixAll.clangd)

## When to use

Invoke `scalpel_fix_lints` (language: **cpp**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.fixAll.clangd]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "cpp"}}
```
