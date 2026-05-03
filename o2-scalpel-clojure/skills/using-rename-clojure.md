---
name: using-rename-clojure
description: When user asks to rename a symbol across the workspace in Clojure, use rename
type: skill
---

# Scalpel - rename (Clojure)

Rename a symbol across the workspace

## When to use

Invoke `rename` (language: **clojure**) when the user says any of:

- "rename this"
- "refactor name"

> v2.0 wire-name cleanup: the legacy alias `scalpel_rename` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "rename", "arguments": {"path": "<file>", "language": "clojure"}}
```
