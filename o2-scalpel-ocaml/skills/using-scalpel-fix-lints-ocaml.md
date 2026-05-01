---
name: using-scalpel-fix-lints-ocaml
description: When user asks to apply all auto-fixable diagnostics (quickfix) in OCaml, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (OCaml)

Apply all auto-fixable diagnostics (quickfix)

## When to use

Invoke `scalpel_fix_lints` (language: **ocaml**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "ocaml"}}
```
