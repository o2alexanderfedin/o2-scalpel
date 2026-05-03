---
name: using-extract-clojure
description: When user asks to extract selection into a function or let-binding in Clojure, use extract
type: skill
---

# Scalpel - extract (Clojure)

Extract selection into a function or let-binding

## When to use

Invoke `extract` (language: **clojure**) when the user says any of:

- "extract this"
- "extract function"
- "extract let"

> v2.0 wire-name cleanup: the legacy alias `scalpel_extract` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.extract]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "extract", "arguments": {"path": "<file>", "language": "clojure"}}
```
