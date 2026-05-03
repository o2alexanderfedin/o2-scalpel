---
name: using-inline-go
description: When user asks to inline a function at all call sites in Go, use inline
type: skill
---

# Scalpel - inline (Go)

Inline a function at all call sites

## When to use

Invoke `inline` (language: **go**) when the user says any of:

- "inline this"
- "inline function"

> v2.0 wire-name cleanup: the legacy alias `scalpel_inline` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.inline]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "inline", "arguments": {"path": "<file>", "language": "go"}}
```
