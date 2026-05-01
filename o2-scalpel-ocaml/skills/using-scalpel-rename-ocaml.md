---
name: using-scalpel-rename-ocaml
description: When user asks to rename a symbol across the workspace in OCaml, use scalpel_rename
type: skill
---

# Scalpel - rename (OCaml)

Rename a symbol across the workspace

## When to use

Invoke `scalpel_rename` (language: **ocaml**) when the user says any of:

- "rename this"
- "refactor name"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "scalpel_rename", "arguments": {"path": "<file>", "language": "ocaml"}}
```
