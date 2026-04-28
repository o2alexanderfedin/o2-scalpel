---
name: using-scalpel-split-file-java
description: When user asks to split a java file along class/method boundaries in Java, use scalpel_split_file
type: skill
---

# Scalpel - split_file (Java)

Split a Java file along class/method boundaries

## When to use

Invoke `scalpel_split_file` (language: **java**) when the user says any of:

- "split this file"
- "extract class"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_split_file", "arguments": {"path": "<file>", "language": "java"}}
```
