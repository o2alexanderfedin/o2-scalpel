---
name: using-scalpel-organize-imports-haxe
description: When user asks to remove unused imports and sort import order in Haxe, use scalpel_organize_imports
type: skill
---

# Scalpel - organize_imports (Haxe)

Remove unused imports and sort import order

## When to use

Invoke `scalpel_organize_imports` (language: **haxe**) when the user says any of:

- "organize imports"
- "sort imports"
- "clean imports"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.organizeImports]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_organize_imports", "arguments": {"path": "<file>", "language": "haxe"}}
```
