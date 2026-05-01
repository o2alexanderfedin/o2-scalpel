---
name: using-scalpel-extract-clojure
description: When user asks to extract selection into a function or let-binding in Clojure, use scalpel_extract
type: skill
---

# Scalpel - extract (Clojure)

Extract selection into a function or let-binding

## When to use

Invoke `scalpel_extract` (language: **clojure**) when the user says any of:

- "extract this"
- "extract function"
- "extract let"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.extract]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_extract", "arguments": {"path": "<file>", "language": "clojure"}}
```
