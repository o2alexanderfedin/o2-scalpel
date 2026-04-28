---
name: using-scalpel-extract-go
description: When user asks to extract selection into a function or variable in Go, use scalpel_extract
type: skill
---

# Scalpel - extract (Go)

Extract selection into a function or variable

## When to use

Invoke `scalpel_extract` (language: **go**) when the user says any of:

- "extract this"
- "extract function"
- "extract variable"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.extract]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_extract", "arguments": {"path": "<file>", "language": "go"}}
```
