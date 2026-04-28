---
name: using-scalpel-extract-cpp
description: When user asks to extract selection into a function in C/C++, use scalpel_extract
type: skill
---

# Scalpel - extract (C/C++)

Extract selection into a function

## When to use

Invoke `scalpel_extract` (language: **cpp**) when the user says any of:

- "extract this"
- "extract function"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.extract]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_extract", "arguments": {"path": "<file>", "language": "cpp"}}
```
