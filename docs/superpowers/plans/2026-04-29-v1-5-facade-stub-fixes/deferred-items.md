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
