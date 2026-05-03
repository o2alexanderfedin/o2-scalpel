---
name: using-fix-lints-cpp
description: When user asks to apply all auto-fixable diagnostics (source.fixall.clangd) in C/C++, use fix_lints
type: skill
---

# Scalpel - fix_lints (C/C++)

Apply all auto-fixable diagnostics (source.fixAll.clangd)

## When to use

Invoke `fix_lints` (language: **cpp**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

> v2.0 wire-name cleanup: the legacy alias `scalpel_fix_lints` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.fixAll.clangd]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "fix_lints", "arguments": {"path": "<file>", "language": "cpp"}}
```
