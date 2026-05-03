---
name: using-split-file-typescript
description: When user asks to split a typescript/javascript file along symbol boundaries in TypeScript, use split_file
type: skill
---

# Scalpel - split_file (TypeScript)

Split a TypeScript/JavaScript file along symbol boundaries

## When to use

Invoke `split_file` (language: **typescript**) when the user says any of:

- "split this file"
- "extract symbols"

> v2.0 wire-name cleanup: the legacy alias `scalpel_split_file` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "split_file", "arguments": {"path": "<file>", "language": "typescript"}}
```
