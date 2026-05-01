---
name: using-scalpel-fix-lints-systemverilog
description: When user asks to apply diagnostic quick-fixes (lint warnings, syntax issues) in SystemVerilog, use scalpel_fix_lints
type: skill
---

# Scalpel - fix_lints (SystemVerilog)

Apply diagnostic quick-fixes (lint warnings, syntax issues)

## When to use

Invoke `scalpel_fix_lints` (language: **systemverilog**) when the user says any of:

- "fix all"
- "fix lints"
- "auto fix"

## How it works

The facade composes the following LSP primitives in order:

1. `textDocument/codeAction[quickfix]`
2. `workspace/applyEdit`

## Tool call

```json
{"tool": "scalpel_fix_lints", "arguments": {"path": "<file>", "language": "systemverilog"}}
```
