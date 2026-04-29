---
name: using-scalpel-organize-imports-csharp
description: When user asks to remove unused using directives and sort import order in C#, use scalpel_organize_imports
type: skill
---

# Scalpel - organize_imports (C#)

Remove unused using directives and sort import order

## When to use

Invoke `scalpel_organize_imports` (language: **csharp**) when the user says any of:

- "organize imports"
- "sort imports"
- "clean imports"
- "organize usings"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.organizeImports]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_organize_imports", "arguments": {"path": "<file>", "language": "csharp"}}
```
