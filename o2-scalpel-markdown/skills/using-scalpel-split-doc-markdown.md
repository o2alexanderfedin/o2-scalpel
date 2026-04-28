---
name: using-scalpel-split-doc-markdown
description: When user asks to split a long markdown doc along h1/h2 boundaries into linked sub-docs in Markdown, use scalpel_split_doc
type: skill
---

# Scalpel - split_doc (Markdown)

Split a long markdown doc along H1/H2 boundaries into linked sub-docs

## When to use

Invoke `scalpel_split_doc` (language: **markdown**) when the user says any of:

- "split this doc"
- "split markdown"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/documentSymbol`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_split_doc", "arguments": {"path": "<file>", "language": "markdown"}}
```
