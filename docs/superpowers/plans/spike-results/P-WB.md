# P-WB - workspace-boundary rule on calcrs seed

**Outcome:** 5/5 cases match expected.

## Cases

| Case | Expected | Observed | Result |
|---|---|---|---|
| inside main workspace | True | True | OK |
| outside (registry) | False | False | OK |
| outside (random tmp) | False | False | OK |
| extra_paths included | True | True | OK |
| extra_paths NOT included | False | False | OK |

## Failures

0 failing case(s): `[]`

## Decision

- 0 failures -> adopt `is_in_workspace(target, roots)` verbatim in the
  Stage 1A `WorkspaceEditApplier` per Q4 §7.1. The `OutsideWorkspace`
  annotation is advisory; the path filter is enforcement.
- >0 failures -> tighten canonicalization (`os.path.realpath` + symlink
  audit) and revisit on Windows (case-insensitive drives, UNC, 8.3 names).

`extra_paths` proves `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` plumbing works:
vendored crates outside LSP-reported workspace folders can be allow-listed
without weakening the boundary for unrelated paths.
