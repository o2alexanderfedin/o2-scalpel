---
name: using-split-file-python
description: When user asks to split a python module along symbol boundaries in Python, use split_file
type: skill
---

# Scalpel - split_file (Python)

Split a Python module along symbol boundaries

## When to use

Invoke `split_file` (language: **python**) when the user says any of:

- "split module"
- "extract symbols"

> v2.0 wire-name cleanup: the legacy alias `scalpel_split_file` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "split_file", "arguments": {"path": "<file>", "language": "python"}}
```
