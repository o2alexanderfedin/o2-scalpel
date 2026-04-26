# Stage 1F — Capability Catalog + Drift CI — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1f-capability-catalog (submodule); feature/stage-1f-capability-catalog (parent)
Author: AI Hive(R)
Built on: stage-1e-python-strategies-complete

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0 | Bootstrap branches + ledger + verify Stage 1E exports     | e188af6d | GREEN | — |
| T1 | capabilities.py — CapabilityRecord + CapabilityCatalog    | c46a2248 | GREEN (7/7) | — |
| T2 | capabilities.py — build_capability_catalog() factory      | 95771600 | GREEN (15/15) | — |
| T3 | capabilities.py — _introspect_adapter_kinds()             | 09bb7a27 | GREEN (21/21) | — |
| T4 | golden-file baseline + --update-catalog-baseline plumbing | df9e4437 | GREEN (27/27 PASS, 1 SKIP) | — |
| T5 | drift gate test (test_stage_1f_t5_catalog_drift.py)       | 50e60403 | GREEN (30/30 PASS, 1 SKIP) | — |
| T6 | __init__.py registry + smoke + ledger close + ff-merge    | _pending_ | _pending_ | — |

## Decisions log

(append-only; one bullet per decision with date + rationale)

- 2026-04-25 — Parent branch is `feature/stage-1f-capability-catalog` directly (no separate planning branch). Plan note about `feature/plan-stage-1f` was outdated; develop was clean at entry, so used `git flow feature start stage-1f-capability-catalog`.

## Stage 1E entry baseline

- Submodule `main` head at Stage 1F start: `e188af6d8e4eafbaee87548be59764d2ee028463`
- Parent branch head at Stage 1F start: `f6febe6` (chore/pause-handoff-2026-04-25 → develop merged)
- Stage 1E tag: `stage-1e-python-strategies-complete`
- Stage 1E suite green: 356/356 (per memory note `project_stage_1e_complete`)

## Source-of-truth pointers (carryover for context)

- §12.1 `CapabilityDescriptor` shape — `CapabilityRecord` is a Stage 1F superset (adds `extension_allow_list`, drops `applies_to_kinds` until Stage 2A).
- §12.3 catalog drift test — Stage 1F implements this exactly: live introspection vs. checked-in JSON, fail on diff, regenerate via CLI flag.
- §14.1 row 15 — file budget `+200 LoC` for `capabilities.py`. Stage 1F holds within this.
- §11.6 `ProvenanceLiteral` — closed set used as `CapabilityRecord.source_server` Literal type.
