---
name: using-scalpel-organize-links-markdown
description: When user asks to sort and normalize markdown links/wiki-links in Markdown, use scalpel_organize_links
type: skill
---

# Scalpel - organize_links (Markdown)

Sort and normalize markdown links/wiki-links

## When to use

Invoke `scalpel_organize_links` (language: **markdown**) when the user says any of:

- "organize links"
- "sort links"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/documentLink`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_organize_links", "arguments": {"path": "<file>", "language": "markdown"}}
```
