---
name: using-scalpel-rename-perl
description: When user asks to rename a symbol within the current file in Perl, use scalpel_rename
type: skill
---

# Scalpel - rename (Perl)

Rename a symbol within the current file

## When to use

Invoke `scalpel_rename` (language: **perl**) when the user says any of:

- "rename this"
- "refactor name"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "scalpel_rename", "arguments": {"path": "<file>", "language": "perl"}}
```
