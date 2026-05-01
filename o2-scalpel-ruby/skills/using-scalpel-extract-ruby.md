---
name: using-scalpel-extract-ruby
description: When user asks to extract selection into a method or variable in Ruby, use scalpel_extract
type: skill
---

# Scalpel - extract (Ruby)

Extract selection into a method or variable

## When to use

Invoke `scalpel_extract` (language: **ruby**) when the user says any of:

- "extract this"
- "extract method"
- "extract variable"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[refactor.extract]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_extract", "arguments": {"path": "<file>", "language": "ruby"}}
```
