---
name: using-scalpel-generate-java
description: When user asks to generate constructors, getters/setters, hashcode/equals, or tostring in Java, use scalpel_generate
type: skill
---

# Scalpel - generate (Java)

Generate constructors, getters/setters, hashCode/equals, or toString

## When to use

Invoke `scalpel_generate` (language: **java**) when the user says any of:

- "generate constructor"
- "generate getter"
- "generate setter"
- "generate equals"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.generate]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_generate", "arguments": {"path": "<file>", "language": "java"}}
```
