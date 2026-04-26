---
name: using-scalpel-split-file-python
description: When user asks to split a python module along symbol boundaries in Python, use scalpel_split_file
type: skill
---

# Scalpel - split_file (Python)

Split a Python module along symbol boundaries

## When to use

Invoke `scalpel_split_file` (language: **python**) when the user says any of:

- "split module"
- "extract symbols"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_split_file", "arguments": {"path": "<file>", "language": "python"}}
```
