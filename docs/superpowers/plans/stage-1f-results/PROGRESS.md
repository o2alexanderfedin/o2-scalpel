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
| T6 | __init__.py registry + smoke + ledger close + ff-merge    | 8b6cae51 | GREEN (5/5; full spike suite 391/391 PASS + 1 SKIP) | — |

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

## Exit summary

- Stage 1F complete 2026-04-25.
- Production LoC: capabilities.py 275, __init__.py +10, conftest.py +39 = 324 total (slightly over the ~205 budget; capabilities.py grew with adapter map + introspection helper docstrings — within acceptable margin).
- Test LoC: ~520 across 6 spike test files.
- Data file: capability_catalog_baseline.json (13 records — 7 Python + 6 Rust, ~3.5 KB).
- Submodule tag: stage-1f-capability-catalog-complete.
- Parent tag: stage-1f-capability-catalog-complete.
- Spike-suite: 392 collected (391 PASS, 1 SKIP — the gated regeneration test).
- Stage 1G entry baseline: this exit SHA.

### Per-task test breakdown

| Task | New tests | Suite total after task |
|---|---|---|
| T1 | 7 | 7 |
| T2 | 8 | 15 |
| T3 | 6 | 21 |
| T4 | 6 + 1 SKIP | 28 (27 PASS, 1 SKIP) |
| T5 | 3 | 31 (30 PASS, 1 SKIP) |
| T6 | 5 | 36 (35 PASS, 1 SKIP) |

### Deferred items routed forward

- `scalpel_capabilities_list` + `scalpel_capability_describe` MCP tools — **Stage 1G** (consumes `build_capability_catalog`).
- `preferred_facade` field population — **Stage 2A** when ergonomic facades land.
- `applies_to_kinds` field — **Stage 2A** when symbol-kind taxonomy lands; will require schema_version bump + re-baseline.
- Live-LSP catalog cross-check — **Stage 1H** integration tests against live `calcrs` + `calcpy` fixtures.
- Plugin/skill code-generator (`o2-scalpel-newplugin`) — **Stage 1J** consumes the catalog.
