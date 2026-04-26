---
name: using-scalpel-split-file-rust
description: When user asks to split a file along symbol boundaries in Rust, use scalpel_split_file
type: skill
---

# Scalpel - split_file (Rust)

Split a file along symbol boundaries

## When to use

Invoke `scalpel_split_file` (language: **rust**) when the user says any of:

- "split this file"
- "extract symbols"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_split_file", "arguments": {"path": "<file>", "language": "rust"}}
```
