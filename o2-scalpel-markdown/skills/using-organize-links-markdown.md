---
name: using-organize-links-markdown
description: When user asks to sort and normalize markdown links/wiki-links in Markdown, use organize_links
type: skill
---

# Scalpel - organize_links (Markdown)

Sort and normalize markdown links/wiki-links

## When to use

Invoke `organize_links` (language: **markdown**) when the user says any of:

- "organize links"
- "sort links"

> v2.0 wire-name cleanup: the legacy alias `scalpel_organize_links` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/documentLink`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "organize_links", "arguments": {"path": "<file>", "language": "markdown"}}
```
