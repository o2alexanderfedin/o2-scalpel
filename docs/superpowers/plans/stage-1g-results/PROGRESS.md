# Stage 1G — Primitive / Safety / Diagnostics MCP Tools — PROGRESS Ledger

Plan: [`../2026-04-24-stage-1g-primitive-tools.md`](../2026-04-24-stage-1g-primitive-tools.md)
Submodule branch: `feature/stage-1g-primitive-tools` (off `main` @ `546f9ff7`)
Parent branch: `feature/stage-1g-primitive-tools`

| Task | Title | Submodule SHA | Outcome | Follow-ups |
|---|---|---|---|---|
| T0 | Bootstrap branches + ledger + verify imports        | 9bf43bd6 | OK — submodule branch open, Stage 1F exports verified | — |
| T1 | scalpel_schemas.py — pydantic v2 IO schemas         | 1313ecf0 | OK — 9/9 green | — |
| T2 | scalpel_runtime.py — ScalpelRuntime singleton       | 75be9fa2 | OK — 7/7 green | LanguageStrategy ctor takes pool: LspPool (plan deviation; documented in commit) |
| T3 | ScalpelCapabilitiesListTool + CapabilityDescribeTool| 6eef844e | OK — 8/8 green | — |
| T4 | ScalpelApplyCapabilityTool                          | ec5ac696 | OK — 5/5 green | merge_code_actions sig adapted (plan deviation) |
| T5 | ScalpelDryRunComposeTool                            | c089c286 | OK — 6/6 green | txn_ prefix added in tool layer (plan deviation) |
| T6 | ScalpelRollbackTool + TransactionRollbackTool       | 07bd6627 | OK — 6/6 green | — |
| T7 | ScalpelWorkspaceHealthTool                          | _pending_ | _pending_ | — |
| T8 | ScalpelExecuteCommandTool                           | _pending_ | _pending_ | — |
| T9 | __init__ re-export + smoke + ff-merge + tag         | _pending_ | _pending_ | — |
