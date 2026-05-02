---
name: using-scalpel-rename-symbol-solidity
description: When user asks to rename a symbol across the workspace in Solidity, use scalpel_rename_symbol
type: skill
---

# Scalpel - rename_symbol (Solidity)

Rename a symbol across the workspace

## When to use

Invoke `scalpel_rename_symbol` (language: **solidity**) when the user says any of:

- "rename this"
- "refactor name"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "scalpel_rename_symbol", "arguments": {"path": "<file>", "language": "solidity"}}
```
