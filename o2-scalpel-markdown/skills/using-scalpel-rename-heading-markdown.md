---
name: using-scalpel-rename-heading-markdown
description: When user asks to rename a heading and update all cross-file wiki-links in Markdown, use scalpel_rename_heading
type: skill
---

# Scalpel - rename_heading (Markdown)

Rename a heading and update all cross-file wiki-links

## When to use

Invoke `scalpel_rename_heading` (language: **markdown**) when the user says any of:

- "rename heading"
- "refactor heading"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "scalpel_rename_heading", "arguments": {"path": "<file>", "language": "markdown"}}
```
