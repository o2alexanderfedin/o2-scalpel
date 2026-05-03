---
name: using-extract-cpp
description: When user asks to extract selection into a function in C/C++, use extract
type: skill
---

# Scalpel - extract (C/C++)

Extract selection into a function

## When to use

Invoke `extract` (language: **cpp**) when the user says any of:

- "extract this"
- "extract function"

> v2.0 wire-name cleanup: the legacy alias `scalpel_extract` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.extract]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "extract", "arguments": {"path": "<file>", "language": "cpp"}}
```
