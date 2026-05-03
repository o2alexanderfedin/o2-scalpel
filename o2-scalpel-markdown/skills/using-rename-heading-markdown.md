---
name: using-rename-heading-markdown
description: When user asks to rename a heading and update all cross-file wiki-links in Markdown, use rename_heading
type: skill
---

# Scalpel - rename_heading (Markdown)

Rename a heading and update all cross-file wiki-links

## When to use

Invoke `rename_heading` (language: **markdown**) when the user says any of:

- "rename heading"
- "refactor heading"

> v2.0 wire-name cleanup: the legacy alias `scalpel_rename_heading` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/rename`

## Tool call

```json
{"tool": "rename_heading", "arguments": {"path": "<file>", "language": "markdown"}}
```
