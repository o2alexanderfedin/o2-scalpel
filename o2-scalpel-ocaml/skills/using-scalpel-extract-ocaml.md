---
name: using-scalpel-extract-ocaml
description: When user asks to extract selection into a let-binding or function in OCaml, use scalpel_extract
type: skill
---

# Scalpel - extract (OCaml)

Extract selection into a let-binding or function

## When to use

Invoke `scalpel_extract` (language: **ocaml**) when the user says any of:

- "extract this"
- "extract function"
- "extract let"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.extract]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_extract", "arguments": {"path": "<file>", "language": "ocaml"}}
```
