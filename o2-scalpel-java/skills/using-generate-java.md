---
name: using-generate-java
description: When user asks to generate constructors, getters/setters, hashcode/equals, or tostring in Java, use generate
type: skill
---

# Scalpel - generate (Java)

Generate constructors, getters/setters, hashCode/equals, or toString

## When to use

Invoke `generate` (language: **java**) when the user says any of:

- "generate constructor"
- "generate getter"
- "generate setter"
- "generate equals"

> v2.0 wire-name cleanup: the legacy alias `scalpel_generate` continues to
> work through v2.x and is removed in v2.1. Prefer the unprefixed name in
> new prompts.

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[source.generate]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "generate", "arguments": {"path": "<file>", "language": "java"}}
```
