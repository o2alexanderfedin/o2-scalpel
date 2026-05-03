---
name: using-rewrite-csharp
description: When user asks to apply rewrite transformations (convert, invert, etc.) in C#, use rewrite
type: skill
---

# Scalpel - rewrite (C#)

Apply rewrite transformations (convert, invert, etc.)

## When to use

Invoke `rewrite` (language: **csharp**) when the user says any of:

- "rewrite this"
- "convert to"
- "invert condition"

> v2.0 wire-name cleanup: the legacy alias `scalpel_rewrite` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.rewrite]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "rewrite", "arguments": {"path": "<file>", "language": "csharp"}}
```
