---
name: using-extract-section-markdown
description: When user asks to extract a section into a new file with a back-link in Markdown, use extract_section
type: skill
---

# Scalpel - extract_section (Markdown)

Extract a section into a new file with a back-link

## When to use

Invoke `extract_section` (language: **markdown**) when the user says any of:

- "extract section"
- "extract heading"

> v2.0 wire-name cleanup: the legacy alias `scalpel_extract_section` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/documentSymbol`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "extract_section", "arguments": {"path": "<file>", "language": "markdown"}}
```
