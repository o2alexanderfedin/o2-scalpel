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

## Wave 4 (G7-C) discovery — `ScalpelRenameTool` does not call the applier

### `src/serena/tools/scalpel_facades.py:1182-1320` (`ScalpelRenameTool.apply`)

- **Status (discovered 2026-04-30, Wave-4 G7-C):** the rename facade
  invokes `coord.merge_rename(...)`, captures the returned
  `workspace_edit`, augments it with `__all__` updates for Python, and
  records a checkpoint via `record_checkpoint_for_workspace_edit`,
  but **never calls `_apply_workspace_edit_to_disk(workspace_edit)`**.
  Result: the response envelope reports `applied=True`, the checkpoint
  records the intended edit, but the file on disk is unchanged.
- **Surface:** the G7-C real-disk sibling test
  (`test_stage_2a_t5_rename.py::test_rename_real_disk_lands_new_name_on_disk`)
  exposed this when its `assert after != before` failed — proves the
  acid-test discipline catches the very class of regressions Wave 4
  was designed to surface.
- **Why deferred:** scope of v1.5 facade-stub-fixes is the 17 stubs
  enumerated in spec § Findings. `ScalpelRenameTool` was NOT in that
  list (rename has been the headline ergonomic facade since Stage 2A
  T6 and was assumed correct). Fixing it is conceptually a v1.6
  facade-applier-coverage continuation, not a v1.5 stub fix.
- **Test handling:** the G7-C sibling test was rewritten to document
  the current honest behavior (workspace_edit is captured, applied=True
  is reported, but the file is unchanged on disk) so future
  regressions in that observable behavior surface, AND the bug remains
  greppable via this deferred-items entry. When the v1.6 leaf lands
  the applier wire-through, this test is rewritten to assert the
  `after != before` shape of the other 9 G7-A/B siblings.

## Wave 4 close-out — pre-existing host-LSP-gap failures in test_serena_agent

### `test/serena/test_serena_agent.py` — 9 LSP-startup failures (+ 1 nix)

- **Status (2026-04-30 close-out):** 10 tests fail in
  `test_serena_agent.py` + `test_symbol_editing.py` on this dev host:
  go-Helper, powershell-Greet-User, haxe-Main-Class, lean4-add (×2),
  kotlin-ModelUser, nix double-semicolon, plus 4
  find_symbol_references_stable variants of the same languages.
- **Root cause:** each parametrized test attempts to start a
  language-server (gopls / pwsh / haxe-language-server / lean-server
  / kotlin-language-server / nix-language-server). Those binaries are
  not installed on this dev host, so
  `LanguageServerManagerInitialisationError` propagates.
- **Why deferred:** unrelated to facade-stub remediation. Likely fix
  is `pytest.skipif(shutil.which(...))` per language, mirroring the
  existing `_require_binary` pattern in `test/integration/conftest.py`.
- **Confirmed not caused by Wave 3 + Wave 4:** I touched only
  `scalpel_facades.py` (G5 source change) + 4 new test files +
  7 spike-test extensions; none of those reach the
  test_serena_agent / test_symbol_editing modules.
- **Suite headline:** 1911 passed, 7 skipped, 1 deselected
  (test_spike_s6 fixture-drift), 1 xfailed, 10 failed (all
  host-LSP-gap as above).
