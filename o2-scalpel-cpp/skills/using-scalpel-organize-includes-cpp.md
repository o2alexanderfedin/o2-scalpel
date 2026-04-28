---
name: using-scalpel-organize-includes-cpp
description: When user asks to sort and deduplicate #include directives in C/C++, use scalpel_organize_includes
type: skill
---

# Scalpel - organize_includes (C/C++)

Sort and deduplicate #include directives

## When to use

Invoke `scalpel_organize_includes` (language: **cpp**) when the user says any of:

- "organize includes"
- "sort includes"
- "clean includes"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.organizeImports]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_organize_includes", "arguments": {"path": "<file>", "language": "cpp"}}
```
