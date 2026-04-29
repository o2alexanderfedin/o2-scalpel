# Deferred items — Wave-2 executor

Out-of-scope discoveries surfaced during Wave-2 execution. These were
NOT caused by Wave-2 leaves and are preserved here per executor
scope-boundary discipline.

## Pre-existing test fixture drift

### `test/spikes/test_spike_s6_auto_import_shape.py::test_s6_auto_import_shape`

- **Status:** failing on `feature/v1.5-facade-stub-fixes` HEAD prior to
  any Wave-2 leaf landing (verified by `git stash` / re-run / `git
  stash pop` while executing L-G3a).
- **Root cause:** the test sends a hardcoded LSP position
  `{"line": 61, "character": 30}` into
  `test/spikes/seed_fixtures/calcrs_seed/src/lib.rs`, which is now only
  60 lines (`eof={'line': 60, 'character': 0}`). The submodule's
  `rust_analyzer.py:235` validates the position eagerly and raises
  `ValueError`.
- **Likely fix:** update the seed fixture or the hardcoded coords. Not
  related to facade-stub remediation. Belongs to a fixture-cadence
  cleanup separate from this milestone.

(Not added to scope. Wave-2 leaves do not modify
`test_spike_s6_auto_import_shape.py` or `seed_fixtures/calcrs_seed/`.)

## Stale-mock fallout from Wave-2 HI-5 (`change_visibility` title_match)

### `test/spikes/test_v0_3_0_facade_application.py` — 4 tests

- `test_facade_writes_resolved_edit_to_disk`
- `test_facade_falls_back_to_empty_checkpoint_when_coord_lacks_lookup`
- `test_facade_falls_back_when_get_action_edit_returns_none`
- `test_facade_writes_multi_file_edit`

- **Status:** failing on `feature/v1.5-facade-stub-fixes` HEAD as of
  `1ce85f68` (verified via `git stash` of this Wave-2 work + re-run).
  The Wave-2 HI-5 commit (`82e769ff fix(change_visibility): honor
  target_visibility via title_match`) introduced the regression by
  threading the caller's `target_visibility` into the shared
  dispatcher's `title_match`. The v0.3.0 fakes hardcode `title="x"`,
  which no longer matches the rust-analyzer-style
  `Change visibility to pub` substring expected by the dispatcher.
- **Surface:** `payload["applied"] is False` (vs `True` expected) — the
  facade returns a no-candidate-matched-title-match envelope instead of
  picking the fake action.
- **Root cause:** stale-mock test pattern flagged by spec § Q&A
  discipline. The fix in scope here is to update each fake's
  `title="x"` to a substring-matchable `"Change visibility to pub"` so
  the dispatcher's title_match accepts it.
- **Decision:** these 4 are repaired as part of work-unit-4 (pyright +
  test-cleanup commit at the end of Wave-2 close-out) since they fall
  under "stale tests caused by prior Wave-2 leaves' changes."
- **Status (2026-04-29 — Wave-2 close-out):** RESOLVED in submodule
  commit `50de2db4 fix(tests): pyright cleanup post-Wave-2 (v0.3.0
  stale-mock fallout)`. Each fake's `title="x"` is now `"Change
  visibility to pub"`; all 4 tests pass; per-file pyright remains
  0/0/0.
