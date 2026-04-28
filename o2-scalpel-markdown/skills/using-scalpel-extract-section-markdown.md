---
name: using-scalpel-extract-section-markdown
description: When user asks to extract a section into a new file with a back-link in Markdown, use scalpel_extract_section
type: skill
---

# Scalpel - extract_section (Markdown)

Extract a section into a new file with a back-link

## When to use

Invoke `scalpel_extract_section` (language: **markdown**) when the user says any of:

- "extract section"
- "extract heading"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/documentSymbol`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_extract_section", "arguments": {"path": "<file>", "language": "markdown"}}
```
