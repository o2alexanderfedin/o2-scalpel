---
name: using-organize-includes-cpp
description: When user asks to sort and deduplicate #include directives in C/C++, use organize_includes
type: skill
---

# Scalpel - organize_includes (C/C++)

Sort and deduplicate #include directives

## When to use

Invoke `organize_includes` (language: **cpp**) when the user says any of:

- "organize includes"
- "sort includes"
- "clean includes"

> v2.0 wire-name cleanup: the legacy alias `scalpel_organize_includes` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.organizeImports]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "organize_includes", "arguments": {"path": "<file>", "language": "cpp"}}
```
