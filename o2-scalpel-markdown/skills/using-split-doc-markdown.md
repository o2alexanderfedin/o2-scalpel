---
name: using-split-doc-markdown
description: When user asks to split a long markdown doc along h1/h2 boundaries into linked sub-docs in Markdown, use split_doc
type: skill
---

# Scalpel - split_doc (Markdown)

Split a long markdown doc along H1/H2 boundaries into linked sub-docs

## When to use

Invoke `split_doc` (language: **markdown**) when the user says any of:

- "split this doc"
- "split markdown"

> v2.0 wire-name cleanup: the legacy alias `scalpel_split_doc` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/documentSymbol`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "split_doc", "arguments": {"path": "<file>", "language": "markdown"}}
```
