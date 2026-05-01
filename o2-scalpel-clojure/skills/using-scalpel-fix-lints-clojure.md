---
name: using-scalpel-fix-lints-clojure
description: When user asks to apply clj-kondo + clojure-lsp diagnostic quick-fixes in Clojure, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (Clojure)

Apply clj-kondo + clojure-lsp diagnostic quick-fixes

## When to use

Invoke `scalpel_fix_lints` (language: **clojure**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "clojure"}}
```
