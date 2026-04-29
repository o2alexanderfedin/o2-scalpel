# Over-Plan — STUB Facade Fix v1.6

**Stance**: Comprehensive; every audit gap gets a TDD plan.
**Date**: 2026-04-29
**Sibling**: `minimalist-plan.md` (YAGNI counter-view)
**Audit source**: `docs/superpowers/research/2026-04-29-stub-facade-audit/STUB-FACADE-AUDIT.md`
**Working dir**: `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena`

---

## Executive summary

The audit flagged 4 STUB + 18 HYBRID + 22 INTENTIONAL = 44 facades.
This over-plan ships a TDD plan for **every flagged facade** plus the universal
A5 (Examples blocks) cosmetic gap, totalling **27 plans across 24 PRs** (a few
small plans are batched into shared PRs to amortise CI; see batching column in
the summary table). The over-planner believes:

1. Every silently-dropped parameter is either a contract bug (rip from
   signature) or a documentation bug (opener-tag informational). Both must be
   fixed; the synthesizer can pick the cheaper path per facade.
2. `applied=True` paired with `{"changes": {}}` is a correctness lie regardless
   of staging plan — P1, no exceptions.
3. `_no_op_applier` for rollback is a correctness lie — P1, but we offer a
   fast path-B doc-warning fix for the synthesizer.
4. Examples blocks are routing-fuel for the LLM and must be batched into a
   single fixture-driven PR so they are honest.

The plan inventory ladders from the highest-confidence stubs down to cosmetic
docstring polish. Each plan has RED tests with line-level production targets,
explicit refactor opportunities, and acceptance criteria.

---

## Plan inventory (24 PRs covering 22 audit-flagged facades + 2 cross-cutting)

| Tier | PRs | Facades touched |
|---|---|---|
| P1 (correctness) | 4 | apply_capability, split_python, rollback-pair, snapshot-capture cross-cutting |
| P1 (consequence) | 1 | dry_run_compose `_dry_run_one_step` (P2 in audit, but we promote because it blocks honest preview) |
| P2 (HYBRID — informational policy) | 12 | change_visibility, change_return_type, extract_lifetime, generate_trait_impl_scaffold, introduce_parameter, generate_from_undefined, auto_import_specialized, ignore_diagnostic, extract, inline, imports_organize, tidy_structure |
| P2 (HYBRID — contract gap) | 3 | split_rust groups, expand_macro dry_run, verify_after_refactor dry_run |
| P3 (workspace_health 11-language) | 1 | workspace_health |
| P3 (rename minor) | 1 | rename also_in_strings |
| P3 (Java Phase 2.5) | 1 | generate_constructor + override_methods (batched) |
| P3 (Examples cosmetic) | 1 | A5 universal (43 facades) |

---

## P1 — STUB facades (4 PRs, 4 facades)

### Plan 1: `scalpel_apply_capability` — fix false `applied=True`

**Goal**: `_dispatch_via_coordinator` resolves the winner action's WorkspaceEdit
and applies it to disk before recording the checkpoint, mirroring the canonical
pattern at `scalpel_facades.py:351-356`. The contract `applied=True` becomes
truthful: the checkpoint records the actual edit and disk reflects it.

**RED tests** (write these first under `test/spikes/test_v16_apply_capability_dispatch.py` and `test/integration/test_apply_capability_dispatch_real.py`; must FAIL on current trunk):

1. `test_dispatch_writes_real_edit_to_disk_for_rust_extract_module` — build a
   tiny rust workspace fixture (`fixtures/rust_extract_module_min/`), pick the
   first capability matching `kind == "refactor.extract.module"`, drive
   `tool.apply(capability_id, file, range)` with a populated coordinator
   double whose `merge_code_actions` returns one action with a non-trivial
   resolved edit. Assert: (a) target file's bytes changed; (b)
   `payload["checkpoint_id"]` is non-None; (c)
   `runtime.checkpoint_store().get(cid).applied != {"changes": {}}`.

2. `test_dispatch_records_resolved_edit_not_empty_changes` — patch
   `coord.merge_code_actions` and `_resolve_winner_edit` to return a known
   `WorkspaceEdit`. Call dispatcher. Assert `ckpt_store.get(cid).applied`
   is the same dict (not `{"changes": {}}`).

3. `test_dispatch_dry_run_skips_apply_and_returns_preview_token` — assert
   `dry_run=True` path still no-ops the on-disk apply and emits
   `preview_token`. (Regression guard for the dry_run branch.)

4. `test_dispatch_no_actions_returns_failure_unmodified_disk` — coordinator
   returns `[]`; assert `applied=False`, `failure.code=="SYMBOL_NOT_FOUND"`,
   target file's bytes unchanged.

5. `test_dispatch_threads_params_into_merge_code_actions` (sibling could argue
   YAGNI — over-planner says: prove `params` is plumbed somewhere). Patch
   `merge_code_actions` to capture kwargs; assert the dispatch passed
   `params` either as `context={"only": [...], **params}` or that the dropped
   line `del params, preview_token` is removed.

6. `test_dispatch_resolve_failure_records_empty_changes_with_warning` —
   `_resolve_winner_edit` returns `None`; assert dispatcher returns
   `applied=True` only if disk-applier returned `>0`, otherwise
   `applied=False, no_op=True` with a warning.

7. `test_dispatch_capability_not_available_returns_envelope` — coordinator's
   `supports_kind` returns False; assert envelope shape (the dispatcher
   should also gate, mirroring the named facades). NEW gate.

**GREEN code changes** (`scalpel_primitives.py`):

- **L216**: remove `del params, preview_token  # Stage 2A wires these end-to-end`.
  Decide policy: thread `params` to `coord.merge_code_actions` `context` arg
  OR opener-tag the docstring informational. The over-planner argues
  thread-it: `merge_code_actions` already accepts `**kwargs` per `Stage 1D`.
- **L228-233**: add `if not coord.supports_kind(language.value, capability.kind):
  return RefactorResult(applied=False, ..., failure=...)` — symmetric to the
  named facades.
- **L261-270** (the lie): replace with the canonical post-LSP block:
  ```python
  edit = _resolve_winner_edit(coord, actions[0])
  applied_count = 0
  if isinstance(edit, dict) and edit:
      # Capture snapshot BEFORE apply (cross-cutting Plan 4).
      snapshot = _capture_pre_edit_snapshot(edit)
      applied_count = _apply_workspace_edit_to_disk(edit)
  else:
      edit = {"changes": {}}
      snapshot = {}
  ckpt_id = runtime.checkpoint_store().record(applied=edit, snapshot=snapshot)
  return RefactorResult(
      applied=bool(applied_count),
      no_op=not applied_count,
      diagnostics_delta=_empty_diagnostics_delta(),
      checkpoint_id=ckpt_id,
      duration_ms=elapsed_ms,
      lsp_ops=(LspOpStat(method="textDocument/codeAction",
                          server=capability.source_server,
                          count=1, total_ms=elapsed_ms),),
  )
  ```
- Imports needed at module top: `from .scalpel_facades import _resolve_winner_edit, _apply_workspace_edit_to_disk`.
  Refactor opportunity: relocate both helpers to `facade_support.py` so
  primitives don't import-cycle with facades. (See cross-cutting Refactor 1.)

**Refactor opportunities** (BLUE):
- Extract `_apply_action_to_disk_and_record(coord, action)` helper into
  `facade_support.py` so it is shared between `_split_rust:351-356`,
  `_extract:526-531`, `_inline:648-653`, `_imports_organize:1027-1034`,
  `_tidy_structure:1369-1376`, `_fix_lints:2249-2253`, `_dispatch_single_kind_facade:1156-1163`,
  `_python_dispatch_single_kind:1905-1912`, `_java_generate_dispatch:3045-3050`,
  AND now `_dispatch_via_coordinator`. Today the same 5-line snippet is
  duplicated 9 times. DRY violation flagged in Cross-cutting refactor 1.

**Fixture needs**:
- `test/fixtures/rust_extract_module_min/lib.rs` — 12-line file with one
  `mod foo { pub fn bar() {} }` block that RA can extract.
- `test/fixtures/rust_extract_module_min/Cargo.toml` — `[package] name = "rxm"`.
- Both behind `requires_rust_analyzer` gate (skip when binary missing).

**Acceptance**:
- All 7 RED tests pass on the GREEN branch.
- `pytest test/spikes/test_stage_1g_t4_apply_capability.py` still green
  (existing tests stay valid because `_dispatch_via_coordinator` is still
  patched out — only the new tests exercise the body).
- `git diff --stat scalpel_primitives.py` shows ~12 lines changed, ~5 new
  imports.
- Capability catalog regression check: `test/integration/test_capability_catalog_drift.py`
  remains green (no contract changes).

**Effort**: M (90% of wiring already exists; copy `_split_rust:351-356`
pattern, lift snapshot capture from cross-cutting Plan 4)
**Risk**: medium — could regress callers that relied on always-`applied=True`.
Mitigation: cross-grep call sites of `scalpel_apply_capability` in tests +
plugin specs; the only known caller is the FALLBACK route, which already
expects honest `applied`/`no_op` semantics from named facades.
**Gitflow**: `feature/v1.6-fix-apply-capability` → develop → main; tag `v1.6-p1-apply-capability`

---

### Plan 2: `scalpel_split_file._split_python` — fix no-on-disk-apply + symbol-list ablation

**Goal**: The Python branch (a) calls `_apply_workspace_edit_to_disk(merged)`
before recording the checkpoint, and (b) honors `groups[*]: list[str]` symbol
lists by iterating both keys AND values, calling a new
`_RopeBridge.move_symbols_to_module(file_rel, target_rel, symbol_names)`.

**RED tests** (write these first under `test/spikes/test_v16_split_python_real.py` and extend `test/spikes/test_stage_2a_t2_split_file.py`; must FAIL):

1. `test_split_python_writes_to_disk` — build a real Python workspace
   (`tmp_path/calcpy.py` with `def add(): ...` + `def sub(): ...`), patch
   `_build_python_rope_bridge` to return a fake whose `move_module` returns
   a real `WorkspaceEdit` touching `calcpy.py`. After `tool.apply(...)`:
   assert `(tmp_path / "add_only.py").exists()` (or that the source file's
   content changed). **Currently fails** because the impl never calls
   `_apply_workspace_edit_to_disk`.

2. `test_split_python_honors_symbol_lists` — `groups={"helpers": ["add"], "math": ["sub"]}`;
   patch the bridge to record `move_symbols_to_module` calls; assert the
   bridge was called with each `(target_rel, symbol_list)` pair, not
   `move_module(rel, target_rel)`. **Currently fails** because impl
   iterates `groups.keys()`.

3. `test_split_python_records_real_edit_in_checkpoint` — assert
   `runtime.checkpoint_store().get(cid).applied` equals the merged
   WorkspaceEdit, not an empty dict.

4. `test_split_python_warns_on_partial_symbol_resolution` — symbol list
   contains an unknown name; assert `warnings` tuple is non-empty in
   `RefactorResult` and other symbols still moved.

5. `test_split_python_dropped_params_now_either_threaded_or_explicit` — for
   each of (`parent_layout`, `keep_in_original`, `reexport_policy`,
   `explicit_reexports`, `allow_partial`), assert one of:
   (a) the `del` line still exists AND the docstring opener tags it
   informational with the convention "Note: <param> is informational; ...",
   OR (b) the parameter is threaded (e.g. `keep_in_original=["foo"]` is
   honored — `foo` stays in the original after move).

6. `test_split_python_dry_run_does_not_apply` — regression guard for the
   dry_run branch (must continue to short-circuit).

7. `test_split_python_empty_symbol_list_in_group_is_no_op_for_that_group` —
   `groups={"empty": [], "with_one": ["add"]}`; assert only one move call.

**GREEN code changes**:

- **`scalpel_facades.py:288-290`**: rewrite the inner loop:
  ```python
  for group_name, symbol_names in groups.items():
      target_rel = f"{group_name}.py"
      if not symbol_names:
          continue
      edit, lost = bridge.move_symbols_to_module(rel, target_rel, symbol_names)
      edits.append(edit)
      if lost:
          warnings.append(f"unresolved symbols in {group_name!r}: {lost}")
  ```
- **`scalpel_facades.py:296` (after `_merge_workspace_edits`)**: insert
  `_apply_workspace_edit_to_disk(merged)` before
  `record_checkpoint_for_workspace_edit`.
- **`python_strategy.py:481-545`** (`_RopeBridge`): add
  `move_symbols_to_module(self, source_rel, target_rel, symbol_names: list[str]) -> tuple[dict, list[str]]`.
  Implementation: for each name in `symbol_names`, use
  `rope.refactor.move.MoveGlobal` (rope's per-symbol mover) instead of
  `MoveModule`. Returns `(merged_edit, unresolved_names)`.
  Reference: `rope.refactor.move.MoveGlobal` API
  (https://github.com/python-rope/rope/blob/master/rope/refactor/move.py).
- **`scalpel_facades.py:236-237`**: decide policy on the 5 dropped params.
  Recommended: rip `parent_layout`, `keep_in_original`, `allow_partial` to
  signature-only with opener-tag (these need spec-level design); thread
  `reexport_policy="preserve_public_api"` and `explicit_reexports` through
  to a new `_synthesize_reexport_edits(...)` helper. Or DEFER all 5 to
  v1.7 with explicit informational tag in the docstring opener. Sibling
  YAGNI vote acceptable here.

**Refactor opportunities**:
- The `_apply_workspace_edit_to_disk(merged)` insertion point is identical
  to `_split_rust:353`. Use the cross-cutting `_apply_action_to_disk_and_record`
  helper from Refactor 1.
- `_RopeBridge.move_module` and `move_symbols_to_module` overlap in setup
  (project bind, resource lookup); extract `_with_rope_resource(rel)` ctx
  manager.

**Fixture needs**:
- Extend `test/fixtures/python_split_file/calcpy.py` with `add`, `sub`,
  `mul`, `div` so symbol lists are non-trivial.
- New `test/fixtures/python_split_file/expected_post_split/helpers.py`
  golden artifact for round-trip assertion.

**Acceptance**:
- All 7 RED tests pass.
- Existing `test_stage_2a_t2_split_file.py` tests still pass (especially
  `test_split_file_python_groups_dispatches_rope_per_group`).
- Run `pytest test/serena/refactoring/test_python_strategy.py -k rope` —
  green; no regression in `move_module` callers.
- `python_strategy.py` pyright: 0/0/0.

**Effort**: M (`move_symbols_to_module` is ~30 LoC of rope; on-disk apply
is one line; symbol-list rewrite is ~10 LoC)
**Risk**: medium — `MoveGlobal` may not exist in pinned rope version.
Mitigation: pin-check upfront; fallback to per-symbol `MoveModule` with
synthesized intermediate file if MoveGlobal absent.
**Gitflow**: `feature/v1.6-fix-split-python` → develop → main; tag `v1.6-p1-split-python`

---

### Plan 3: `scalpel_rollback` + `scalpel_transaction_rollback` — wire real inverse-applier (Path A: real fix)

**Goal**: Replace `_no_op_applier` with a real applier so the contract
"`scalpel_rollback(ckpt_id)` writes pre-edit content back to disk" holds. This
plan assumes Path A (real fix) per audit § cross-check 4. If the synthesizer
picks Path B (doc-only warning), drop to Plan 3-alt below.

**RED tests** (write under `test/spikes/test_v16_rollback_real.py`):

1. `test_rollback_restores_file_bytes_after_real_apply` — full round-trip:
   (a) write `tmp_path/calc.py` with content `c0`; (b) call
   `scalpel_rename` (or any facade that mutates) and assert content is now
   `c1 != c0`; (c) call `scalpel_rollback(checkpoint_id_from_step_b)`;
   (d) assert content is `c0` again. **Currently fails** because the
   inverse uses `snapshot={}` so the inverted edit inserts an empty
   string.

2. `test_rollback_uses_real_disk_applier_not_no_op_applier` — patch
   `_no_op_applier` to flag if called; assert it is NOT called by
   `scalpel_rollback.apply` after the rollback succeeds. Instead the new
   `_inverse_applier_to_disk` (resource-op aware) IS called.

3. `test_rollback_handles_documentchanges_resource_ops` — apply a refactor
   that creates a new file (e.g. `scalpel_split_doc`); rollback must
   delete the created file. Currently fails because resource ops are
   skipped per `_apply_workspace_edit_to_disk:134` ("Resource op — skip
   per v1.1 deferral").

4. `test_transaction_rollback_walks_in_reverse_with_real_disk_writes` —
   commit a 2-step compose, rollback the transaction, assert both files
   are at their pre-step-1 state.

5. `test_rollback_idempotent_second_call_is_no_op_unchanged` — regression
   guard: second `scalpel_rollback(cid)` returns `no_op=True` and does
   NOT re-write anything (file remains at pre-edit content from first
   rollback).

6. `test_rollback_unknown_id_returns_no_op_unchanged` — regression guard
   for the existing `if ckpt is None` branch (line 683-689).

7. `test_rollback_partial_failure_surfaces_failure_info` — inverse contains
   a TextEdit referencing a URI that no longer exists; assert
   `applied=False, failure.code="ROLLBACK_PARTIAL"` (NEW error code) with
   per-URI breakdown.

**GREEN code changes**:

- **`scalpel_primitives.py:652-657`**: replace `_no_op_applier` with
  `_inverse_applier_to_disk`:
  ```python
  def _inverse_applier_to_disk(inverse_edit: dict[str, Any]) -> int:
      """Real applier for checkpoint_store.restore — handles both
      TextDocumentEdit AND CreateFile/DeleteFile/RenameFile resource ops
      (which the apply-side _apply_workspace_edit_to_disk skips per its
      v1.1 deferral). Inverse edits emitted by inverse_workspace_edit
      always use the documentChanges shape with explicit kind markers."""
      from .scalpel_facades import _apply_text_edits_to_file_uri
      n = 0
      for dc in inverse_edit.get("documentChanges") or []:
          if not isinstance(dc, dict):
              continue
          kind = dc.get("kind")
          if kind == "create":
              uri, options = dc["uri"], dc.get("options") or {}
              path = _uri_to_path(uri)
              if path is None:
                  continue
              if path.exists() and not options.get("overwrite", False):
                  continue
              path.parent.mkdir(parents=True, exist_ok=True)
              path.write_text("", encoding="utf-8")
              n += 1
          elif kind == "delete":
              uri, options = dc["uri"], dc.get("options") or {}
              path = _uri_to_path(uri)
              if path is None:
                  continue
              if path.exists():
                  path.unlink()
                  n += 1
              elif not options.get("ignoreIfNotExists", False):
                  return -1  # surface partial failure
          elif kind == "rename":
              old, new = _uri_to_path(dc["oldUri"]), _uri_to_path(dc["newUri"])
              if old and new and old.exists():
                  old.rename(new)
                  n += 1
          else:
              # TextDocumentEdit
              uri = (dc.get("textDocument") or {}).get("uri")
              if isinstance(uri, str):
                  n += _apply_text_edits_to_file_uri(uri, dc.get("edits") or [])
      return n
  ```
- **L690 + L727**: replace both `_no_op_applier` references with
  `_inverse_applier_to_disk`.
- Add `_uri_to_path` helper (or import from `scalpel_facades`).
- New `ErrorCode.ROLLBACK_PARTIAL` in `scalpel_schemas.py`.

**Refactor opportunities**:
- Move `_apply_text_edits_to_file_uri` and a new `_apply_resource_op` to
  `facade_support.py` to break the import cycle (primitives→facades).
- Extract `_uri_to_path(uri)` helper currently inline at
  `_apply_text_edits_to_file_uri:154-156` and reuse.

**Fixture needs**:
- `test/fixtures/rollback_round_trip/calc.py` (3 LoC) for the smoke test.
- A two-file fixture for the resource-op test (`test/fixtures/rollback_resource_ops/`).

**Acceptance**:
- All 7 RED tests pass.
- Existing `test_stage_1g_t6_rollback.py` 5 tests still pass:
  `test_single_rollback_unknown_id_returns_no_op` works because
  `if ckpt is None` short-circuits before applier; the empty-snapshot
  cases in the existing tests now genuinely no-op (zero edits in inverse).
- e2e: run `pytest test/e2e/` — no regressions on the 18 e2e scenarios.
- Cross-link: depends on cross-cutting Plan 4 (snapshot capture) for full
  round-trip restoration; without Plan 4, rollback restores to `""` which
  is incorrect. **Plan 3 BLOCKS until Plan 4 lands** (or is sequenced in
  the same PR — recommended).

**Effort**: L (real inverse applier ~50 LoC, partial-failure error code,
2 new fixtures, test cross-cuts); shrinks to M if Plan 4 lands first.
**Risk**: HIGH — rollback semantics affect every checkpoint downstream.
A bug here can corrupt user files. Mitigations: dry_run mode for the
rollback applier (`scalpel_rollback(ckpt, simulate=True)` returns the
inverse-edit JSON without writing), wide e2e regression sweep, document
the snapshot-required precondition.
**Gitflow**: `feature/v1.6-fix-rollback-real-applier` → develop → main;
tag `v1.6-p1-rollback`

#### Plan 3-alt: `scalpel_rollback` + `scalpel_transaction_rollback` (Path B — doc-only warning, S effort)

If synthesizer prefers low-risk doc fix:

**Goal**: Add a giant `WARNING:` block to both class docstrings stating
"rollback marks the checkpoint reverted in the store; it does NOT undo
edits to disk. The caller is responsible for re-running the inverse
refactor or using their editor's undo stack."

**RED tests** (single test, must FAIL):

1. `test_rollback_docstring_carries_disk_warning` — `assert
   "WARNING" in inspect.getdoc(ScalpelRollbackTool)`; same for
   `ScalpelTransactionRollbackTool`.

**GREEN code changes**:
- `scalpel_primitives.py:670-671`: prepend the `WARNING:` block to class docstring.
- Same at `:699-700`.

**Refactor opportunities**: none.
**Fixture needs**: none.
**Acceptance**: the new test passes; existing tests unchanged.
**Effort**: S
**Risk**: low — doc only.
**Gitflow**: `feature/v1.6-rollback-warning-only` → develop → main;
tag `v1.6-p3-rollback-warning`

**Decision flag for synthesizer**: A vs B. Path A is correctness; Path B is
honesty-without-engineering. Recommended hybrid: ship B in v1.6 (S, low risk),
ship A in v1.7 (L, high risk, needs separate deep e2e cycle). The over-planner
prefers A in v1.6 because the contract lie is the most-cited LLM-router footgun
in the audit.

---

### Plan 4 (cross-cutting prerequisite for Plan 3-A): Capture pre-edit snapshot at every applier site

**Goal**: Before any `_apply_workspace_edit_to_disk(edit)` call, capture the
pre-edit content for every URI the edit touches and pass it as `snapshot=`
to `record_checkpoint_for_workspace_edit`. Today every recorder passes
`snapshot={}` so the synthesised inverse contains empty content. Without this,
Plan 3-A cannot restore.

**RED tests** (`test/spikes/test_v16_snapshot_capture.py`):

1. `test_snapshot_captured_at_apply_capability` — before/after `tool.apply()`
   on a fixture, assert `runtime.checkpoint_store().get(cid).snapshot[uri]`
   contains the pre-edit file content (not `""`).

2. `test_snapshot_captured_at_split_python` — same shape, against the
   Python branch.

3. `test_snapshot_captured_at_extract` / `test_snapshot_captured_at_inline` /
   `test_snapshot_captured_at_dispatch_single_kind_facade` /
   `test_snapshot_captured_at_python_dispatch_single_kind` /
   `test_snapshot_captured_at_imports_organize` /
   `test_snapshot_captured_at_tidy_structure` /
   `test_snapshot_captured_at_fix_lints` /
   `test_snapshot_captured_at_java_generate_dispatch` /
   `test_snapshot_captured_at_split_rust` — 9 sites, one test each.

4. `test_snapshot_captured_for_create_file_resource_op` — when the edit
   creates a new file, snapshot for that URI is `_SNAPSHOT_NONEXISTENT`.

5. `test_snapshot_captured_for_delete_file_resource_op` — symmetric.

**GREEN code changes**:

- **New helper** in `facade_support.py`:
  ```python
  def capture_pre_edit_snapshot(workspace_edit: dict[str, Any]) -> dict[str, str]:
      """Capture per-URI pre-edit content for every URI in workspace_edit.
      Returns {uri: content_or_sentinel}. Used by checkpoint_store.record so
      inverse_workspace_edit can synthesise a correct inverse."""
      from urllib.parse import urlparse, unquote
      from .scalpel_facades import _SNAPSHOT_NONEXISTENT  # see import-cycle note
      snapshot: dict[str, str] = {}
      uris: set[str] = set()
      for uri in (workspace_edit.get("changes") or {}).keys():
          uris.add(uri)
      for dc in workspace_edit.get("documentChanges") or []:
          if not isinstance(dc, dict):
              continue
          if "kind" in dc:
              uri = dc.get("uri") or dc.get("oldUri")
              if isinstance(uri, str):
                  uris.add(uri)
          else:
              uri = (dc.get("textDocument") or {}).get("uri")
              if isinstance(uri, str):
                  uris.add(uri)
      for uri in uris:
          if not uri.startswith("file://"):
              continue
          path = Path(unquote(urlparse(uri).path))
          if path.exists():
              try:
                  snapshot[uri] = path.read_text(encoding="utf-8")
              except OSError:
                  snapshot[uri] = ""
          else:
              snapshot[uri] = _SNAPSHOT_NONEXISTENT
      return snapshot
  ```
- **9 call sites** updated to capture+pass snapshot:
  | File | Line | Site |
  |---|---|---|
  | `scalpel_primitives.py` | 261 | `_dispatch_via_coordinator` |
  | `scalpel_facades.py` | 305 | `_split_python` |
  | `scalpel_facades.py` | 356 | `_split_rust` |
  | `scalpel_facades.py` | 531 | `_extract` |
  | `scalpel_facades.py` | 653 | `_inline` |
  | `scalpel_facades.py` | 788 | `_rename` |
  | `scalpel_facades.py` | 1036 | `_imports_organize` |
  | `scalpel_facades.py` | 1161 | `_dispatch_single_kind_facade` |
  | `scalpel_facades.py` | 1378 | `_tidy_structure` |
  | `scalpel_facades.py` | 1910 | `_python_dispatch_single_kind` |
  | `scalpel_facades.py` | 2254 | `_fix_lints` |
  | `scalpel_facades.py` | 2395, 2491, 2594 | python v1.1 facades |
  | `scalpel_facades.py` | 3050 | `_java_generate_dispatch` |
  | `scalpel_facades.py` | 3231 | markdown facades (resource-op aware) |

  At each site, change:
  ```python
  cid = record_checkpoint_for_workspace_edit(workspace_edit=edit, snapshot={})
  ```
  to:
  ```python
  snapshot = capture_pre_edit_snapshot(edit) if edit else {}
  cid = record_checkpoint_for_workspace_edit(workspace_edit=edit, snapshot=snapshot)
  ```

  Order: capture BEFORE `_apply_workspace_edit_to_disk(edit)` so the
  snapshot reflects pre-edit state.

**Refactor opportunities**:
- Combine snapshot-capture + apply + record into a single
  `apply_and_checkpoint(edit) -> str` helper in `facade_support.py`. This
  is the cross-cutting `_apply_action_to_disk_and_record` from Refactor 1
  expanded with snapshot. Replaces the 5-line snippet duplicated 14 times
  across the codebase with one call.

**Fixture needs**: none new (reuse fixtures from Plans 1-2-3).

**Acceptance**:
- All 14 RED tests pass.
- Existing checkpoint-store unit tests
  (`test/spikes/test_stage_1b_t10_inverse_edit.py`,
  `test_stage_1b_t11_checkpoint_store.py`) still green.
- `test/integration/test_apply_source_determinism.py` still green.

**Effort**: M (one new helper + 14 mechanical call-site updates)
**Risk**: medium — touching every applier site; mitigated by mechanical
nature of the change and existing checkpoint-store tests.
**Gitflow**: `feature/v1.6-fix-snapshot-capture` → develop → main; tag
`v1.6-p1-snapshot-capture`. **Sequence as the FIRST P1 PR**, before
Plans 1, 2, 3-A — they all benefit from real snapshots.

---

### Plan 5: `scalpel_dry_run_compose._dry_run_one_step` — promote to P1 from P2

**Goal**: `_dry_run_one_step` invokes the dispatched facade in dry_run mode
and captures its `RefactorResult.preview_token` + the would-be edit. The
returned `StepPreview.changes` is a non-empty tuple iff the routed facade
returns a non-empty resolved edit.

**Why P1 even though audit says P2**: the audit authors hedge ("Spec § P5a
SHIP-B explicitly ratified shipping without shadow simulation"), but the
`_dry_run_one_step` body's lie is structurally identical to `apply_capability`'s
lie — the docstring promises "virtually apply" and the body returns `()`. Per
audit § cross-check 4 the synthesizer notes the "hand-rolled fake" framing.
Over-planner argues P1 because LLMs reading the preview see `changes=()` and
may falsely conclude the transaction is empty.

**RED tests** (`test/spikes/test_v16_dry_run_compose_real.py`):

1. `test_dry_run_one_step_returns_changes_when_facade_returns_edit` — patch
   `_FACADE_DISPATCH[step.tool]` to return a `RefactorResult` with
   non-empty `applied` field; assert `step_preview.changes != ()`.

2. `test_dry_run_one_step_surfaces_failure_when_facade_fails` — patch the
   facade to return `failure!=None`; assert `step_preview.failure is not None`
   without external patching of `_dry_run_one_step` (the existing fail-fast
   tests at `test_apply_records_per_step_preview` and the line-63/125
   tests will need to be re-evaluated; they patch `_dry_run_one_step`
   externally — those mocks should NOW be removed).

3. `test_dry_run_one_step_uses_dry_run_true_to_avoid_disk_writes` — assert
   the facade is called with `dry_run=True`; assert no disk writes occurred
   (compare file mtimes before/after).

4. `test_dry_run_one_step_diagnostics_delta_propagates` — facade returns
   `diagnostics_delta` with new findings; assert preview surfaces those.

5. `test_dry_run_one_step_capability_not_available_envelope_passes_through` —
   facade returns `CAPABILITY_NOT_AVAILABLE`; assert preview surfaces the
   envelope as a warning, not a hard fail.

6. `test_dry_run_compose_5min_ttl_unchanged` — regression guard for
   `PREVIEW_TTL_SECONDS=300`.

**GREEN code changes**:

- **`scalpel_primitives.py:340-360`**: replace the body with:
  ```python
  def _dry_run_one_step(step, *, project_root, step_index) -> StepPreview:
      from .scalpel_facades import _FACADE_DISPATCH
      handler = _FACADE_DISPATCH.get(step.tool)
      if handler is None:
          return StepPreview(
              step_index=step_index, tool=step.tool, changes=(),
              diagnostics_delta=_empty_diagnostics_delta(),
              failure=FailureInfo(
                  stage="_dry_run_one_step",
                  reason=f"Unknown tool {step.tool!r}",
                  code=ErrorCode.INVALID_ARGUMENT, recoverable=False,
              ),
          )
      args = {**(step.args or {}), "dry_run": True}
      try:
          raw = handler(args)
          payload = json.loads(raw)
      except Exception as exc:
          return StepPreview(..., failure=FailureInfo(
              stage="_dry_run_one_step", reason=str(exc),
              code=ErrorCode.INTERNAL, recoverable=True,
          ))
      changes = tuple(_payload_to_step_changes(payload))
      diagnostics_delta = _payload_to_diagnostics_delta(payload) or _empty_diagnostics_delta()
      failure = _payload_to_failure(payload)
      return StepPreview(
          step_index=step_index, tool=step.tool,
          changes=changes,
          diagnostics_delta=diagnostics_delta,
          failure=failure,
      )
  ```
- **New helpers**: `_payload_to_step_changes`, `_payload_to_diagnostics_delta`,
  `_payload_to_failure` to project a `RefactorResult.model_dump_json()` into
  the `StepPreview` schema.
- Existing tests at `test_apply_records_per_step_preview:63,125` must drop
  their `patch("_dry_run_one_step")` external injection — they currently
  pass via mock-and-replace; after this change, they should drive the body
  directly.

**Refactor opportunities**:
- The `_FACADE_DISPATCH` table at `scalpel_facades.py:3273-3365` is a
  module-level dict; importing it in `scalpel_primitives.py` introduces a
  cycle. Resolve via lazy import at call site (already shown above).

**Fixture needs**: none new; reuse `test/spikes/test_stage_1g_t5_dry_run_compose.py` fixtures.

**Acceptance**:
- All 6 RED tests pass.
- Existing `test_stage_1g_t5_dry_run_compose.py` tests pass after dropping
  the external `_dry_run_one_step` mocks.
- `scalpel_transaction_commit` flow continues to work end-to-end.

**Effort**: L (touches the compose grammar, needs payload-projection helpers)
**Risk**: medium — _dry_run_one_step is called by scalpel_dry_run_compose
which fronts every transaction; a bug surfaces in every multi-step LLM
workflow.
**Gitflow**: `feature/v1.6-fix-dry-run-one-step` → develop → main; tag
`v1.6-p1-dry-run-real`

---

## P2 — HYBRID facades: informational-parameter cluster (1 PR, 12 facades)

**Strategy**: ship a single uniform PR that picks the **opener-tag** policy
(not signature-rip) for all 12 facades. Reasons:
- Signature changes break LLM tool registrations and require plugin re-bake.
- The defender's "routing signal" defense becomes honest if the docstring
  opener says so — then the parameter has explicit informational status.
- Shipping the opener-tag uniformly is a 12-facade docstring-only PR;
  sibling YAGNI may want this as the only P2 work.

### Plan 6: Informational-parameter opener-tag batch

**Goal**: For each of 12 facades that `del`s a documented parameter, prepend
`Note: <param>= is informational; rust-analyzer/ruff/pyright selects the
exact rewrite per cursor.` (or the language-appropriate variant) to the
class docstring opener AND to the `:param <param>:` line. This makes the
defender's argument honest.

**RED tests** (`test/spikes/test_v16_informational_param_opener.py`):

For each of the 12 facades, one test asserting the docstring opener
contains the substring `informational`:

1. `test_change_visibility_target_visibility_informational_in_opener`
2. `test_change_return_type_new_return_type_informational_in_opener`
3. `test_extract_lifetime_lifetime_name_informational_in_opener`
4. `test_generate_trait_impl_scaffold_trait_name_informational_in_opener`
5. `test_introduce_parameter_parameter_name_informational_in_opener`
6. `test_generate_from_undefined_target_kind_informational_or_threaded`
7. `test_auto_import_specialized_symbol_name_informational_in_opener`
8. `test_ignore_diagnostic_rule_informational_or_threaded`
9. `test_extract_dropped_params_informational_block_in_docstring`
   (`new_name`, `visibility`, `similar`, `global_scope`)
10. `test_inline_dropped_params_informational_block` (`name_path`,
    `remove_definition`)
11. `test_imports_organize_dropped_toggles_informational_block`
    (`add_missing`, `remove_unused`, `reorder`)
12. `test_tidy_structure_scope_informational_in_opener`

For TWO of the 12 (`generate_from_undefined.target_kind` and
`ignore_diagnostic.rule`), the test body should ALSO check that an attempt
was made to thread the parameter through `merge_code_actions(only=[...])`
filtering — these are routing knobs that CAN be honored, unlike the rust
ones. So those two facades have a dual fix: opener-tag + filter.

**GREEN code changes** (per facade — class docstring + `:param:` block):

- `scalpel_facades.py:1253-1255` (ScalpelChangeVisibilityTool): prepend opener.
- `scalpel_facades.py:1464-1466` (ScalpelChangeReturnTypeTool): same.
- `scalpel_facades.py:1550-1552` (ScalpelExtractLifetimeTool): same.
- `scalpel_facades.py:1641-1643` (ScalpelGenerateTraitImplScaffoldTool): same;
  ALSO consider: `trait_name` is a *required* positional — should be
  threaded through `coord.execute_command` for rust-analyzer's
  `extractTrait` LSP command, not opener-tagged. Defer to v1.7 if
  threading is non-trivial; keep opener-tag for v1.6.
- `scalpel_facades.py:2050-2052` (ScalpelIntroduceParameterTool): same.
- `scalpel_facades.py:2097-2099` (ScalpelGenerateFromUndefinedTool): opener-tag
  AND thread `target_kind` to filter actions: after `merge_code_actions`,
  filter `actions = [a for a in actions if a.title.lower().startswith(target_kind)]`.
- `scalpel_facades.py:2139-2141` (ScalpelAutoImportSpecializedTool): opener-tag.
  Note: docstring already has "v1.1 will expose a candidate-set parameter" —
  remove that promise (4 versions overdue) and replace with the informational
  tag.
- `scalpel_facades.py:2273-2275` (ScalpelIgnoreDiagnosticTool): opener-tag
  AND thread `rule` to filter actions: `actions = [a for a in actions if
  rule in str(a.diagnostics or [])]` (or similar). The defender's claim that
  this is informational is weakest here — the user requesting `# noqa: E501`
  vs `# noqa: F401` has a real preference. Try threading first.
- `scalpel_facades.py:403-440` (ScalpelExtractTool): opener-tag block listing
  all 4 dropped params.
- `scalpel_facades.py:560-591` (ScalpelInlineTool): opener-tag block listing
  `name_path` and `remove_definition`. ALSO consider: `name_path` could be
  threaded the same way `_extract:486-490` does it via
  `coord.find_symbol_range`. Mid-effort enhancement; recommend split into
  Plan 6-bonus (S effort).
- `scalpel_facades.py:929-958` (ScalpelImportsOrganizeTool): opener-tag block
  listing 3 toggles. Note: these CAN be threaded via
  `coord.merge_code_actions(only=[...])` with kind suffixes —
  `source.organizeImports.add_missing`, `source.organizeImports.remove_unused`.
  Pylsp/ruff don't currently advertise those finer kinds, so opener-tag is
  the honest path for v1.6; revisit when LSP advertises sub-kinds.
- `scalpel_facades.py:1300-1325` (ScalpelTidyStructureTool): opener-tag for
  `scope`. ALSO: scope threading is straightforward — when `scope='type'` or
  `scope='impl'`, restrict `_TIDY_STRUCTURE_KINDS` to just
  `("refactor.rewrite.reorder_fields",)` for type, or
  `("refactor.rewrite.reorder_impl_items",)` for impl. Simple ~5-line filter.
  Recommend threading.

**Refactor opportunities**:
- A new module-level constant `_INFORMATIONAL_PARAM_NOTE_TEMPLATE` that
  formats consistently across facades.
- A docstring lint test `test_dropped_params_carry_informational_tag` that
  parses each facade's `apply()` AST, finds `del <name>` lines, and asserts
  `f"{name}= is informational"` appears in the class or method docstring.
  CI gate against future regressions.

**Fixture needs**: none.

**Acceptance**:
- All 12 RED tests pass.
- New CI gate `test_dropped_params_carry_informational_tag` is added to
  `test/integration/test_facade_docstring_invariants.py` and runs in the
  default suite.
- For the 2 facades that thread parameters (`generate_from_undefined`,
  `ignore_diagnostic`, also opt-in `tidy_structure`, `inline.name_path` if
  Plan 6-bonus lands), the new threaded-param tests assert the post-filter
  action selection respects the parameter.

**Effort**: M (12 docstring updates + 2-3 small filter implementations +
1 CI gate test)
**Risk**: low — docstrings only for the 9 unchanged-behavior cases; small
behavior change for 3-4 threaded cases.
**Gitflow**: `feature/v1.6-informational-param-batch` → develop → main;
tag `v1.6-p2-informational-batch`

---

## P2 — HYBRID facades: contract gaps (3 PRs, 3 facades)

### Plan 7: `scalpel_split_file._split_rust` — honor `groups` via execute_command

**Goal**: Thread `groups: dict[str, list[str]]` to rust-analyzer's
`extractModule` command via `coord.execute_command` so the user's grouping
intent is honored. If RA does not advertise `extractModule` as a command,
fall back to the current "RA picks" behavior with an explicit warning.

**RED tests** (`test/spikes/test_v16_split_rust_groups.py`):

1. `test_split_rust_threads_groups_to_execute_command_when_advertised` —
   patch `coord.execute_command_allowlist` to include `rust-analyzer.extractModule`;
   call `tool.apply(file=lib_rs, groups={"a": ["foo"], "b": ["bar"]})`;
   assert `coord.execute_command` was called with the groups payload.

2. `test_split_rust_falls_back_to_codeaction_when_not_advertised` — allowlist
   missing; assert codeaction path runs AND `warnings` contains
   `"groups parameter ignored"`.

3. `test_split_rust_dropped_groups_warning_visible_in_result` — regression:
   when fallback happens, the warning surfaces in `RefactorResult.warnings`.

**GREEN code changes**:

- `scalpel_facades.py:319-368` (`_split_rust`): replace `del groups` with:
  ```python
  cmd_set = coord.execute_command_allowlist or set()
  if "rust-analyzer.extractModule" in cmd_set and groups:
      result = _run_async(coord.execute_command(
          command="rust-analyzer.extractModule",
          arguments=[{"file": file, "groups": groups}],
      ))
      # ... apply the resulting WorkspaceEdit ...
  else:
      warnings.append(
          "scalpel_split_file: rust-analyzer does not expose extractModule "
          "as an executeCommand; groups parameter ignored, RA's first "
          "refactor.extract.module assist drives the output."
      )
      # ... existing codeAction path ...
  ```

**Refactor opportunities**:
- Reuse the `_apply_action_to_disk_and_record` helper from Refactor 1.

**Fixture needs**: extend `test/fixtures/rust_extract_module_min/` with a
`groups`-shaped scenario.

**Acceptance**: all 3 RED tests pass; existing
`test_split_file_rust_dispatches_coordinator` still green.

**Effort**: M
**Risk**: medium — RA's `extractModule` command shape is undocumented;
needs spike test against real RA binary first.
**Gitflow**: `feature/v1.6-split-rust-groups` → develop → main; tag
`v1.6-p2-split-rust`

### Plan 8: `scalpel_expand_macro` — honor `dry_run`

**Goal**: When `dry_run=True`, return the expansion in `RefactorResult.preview_token`
without setting `applied=True`. Today `del preview_token, dry_run` ablates
both; the contract says "dry_run: preview only".

**RED tests** (`test/spikes/test_v16_expand_macro_dry_run.py`):

1. `test_expand_macro_dry_run_returns_applied_false` — `dry_run=True`;
   assert `applied=False, no_op=False, preview_token != None`.
2. `test_expand_macro_default_apply_true_returns_expansion` — `dry_run=False`;
   regression guard.
3. `test_expand_macro_dry_run_still_includes_expansion_in_findings` — the
   expansion text is preserved in `language_findings`.

**GREEN code changes**:

- `scalpel_facades.py:1741-1799` (`ScalpelExpandMacroTool`): remove `del dry_run`
  from line 1760; add a branch:
  ```python
  if dry_run:
      return RefactorResult(
          applied=False, no_op=False,
          preview_token=f"pv_expand_macro_{int(time.time())}",
          language_findings=(finding,),
          ...
      )
  ```

**Refactor opportunities**: none.
**Fixture needs**: needs RA binary to actually expand a macro; gated by
`requires_rust_analyzer`.
**Acceptance**: 3 RED tests pass.
**Effort**: S
**Risk**: low.
**Gitflow**: `feature/v1.6-expand-macro-dry-run` → develop → main; tag
`v1.6-p2-expand-macro`

### Plan 9: `scalpel_verify_after_refactor` — honor `dry_run`

**Goal**: Same as Plan 8 — return preview without running flycheck/runnables
when `dry_run=True`. Currently `del preview_token, dry_run` ablates both;
contract says preview only.

**RED tests** (`test/spikes/test_v16_verify_after_refactor_dry_run.py`):

1. `test_verify_dry_run_skips_flycheck_call` — patch `coord.run_flycheck`;
   assert NOT called when `dry_run=True`.
2. `test_verify_dry_run_skips_runnables_call` — same for `coord.fetch_runnables`.
3. `test_verify_dry_run_returns_preview_token_no_findings` — assert empty
   `language_findings` and `preview_token != None`.
4. `test_verify_default_apply_calls_both_endpoints` — regression guard.

**GREEN code changes**:

- `scalpel_facades.py:1805-1862` (`ScalpelVerifyAfterRefactorTool`): remove
  `del dry_run` (line 1824); add early-return:
  ```python
  if dry_run:
      return RefactorResult(
          applied=False, no_op=False,
          preview_token=f"pv_verify_{int(time.time())}",
          ...
      ).model_dump_json(indent=2)
  ```

**Refactor opportunities**: none.
**Fixture needs**: existing.
**Acceptance**: 4 RED tests pass.
**Effort**: S
**Risk**: low.
**Gitflow**: `feature/v1.6-verify-after-refactor-dry-run` → develop → main;
tag `v1.6-p2-verify-after-refactor`

---

## P3 — Workspace health & minor (3 PRs)

### Plan 10: `scalpel_workspace_health` — iterate all 11 v1.4 languages

**Goal**: Replace the hardcoded `(Language.PYTHON, Language.RUST)` loop at
`scalpel_primitives.py:832` with iteration over the 11 supported languages
the catalog advertises (Python, Rust, TypeScript, Go, C++, Java, Lean4,
SMT2, Prolog, Markdown, ProbLog).

**RED tests** (extend `test/spikes/test_stage_1g_t7_workspace_health.py`):

1. `test_workspace_health_includes_typescript_in_language_keys` — assert
   `payload["languages"]["typescript"]` exists, even if no TS server runs.
2. `test_workspace_health_includes_all_v14_languages` — parametrized over
   the 11 languages; assert each appears in `payload["languages"]`.
3. `test_workspace_health_unknown_language_surfaces_failed_state` — when a
   language has no live server, `indexing_state == "not_started"` (not an
   error).
4. `test_workspace_health_dynamic_capabilities_listed_per_language` —
   regression guard for `dynamic_capabilities`.

**GREEN code changes**:

- `scalpel_primitives.py:832`: replace tuple with:
  ```python
  _SUPPORTED_LANGUAGES = (
      Language.PYTHON, Language.RUST, Language.TYPESCRIPT, Language.GO,
      Language.CPP, Language.JAVA, Language.LEAN4, Language.SMT2,
      Language.PROLOG, Language.MARKDOWN, Language.PROBLOG,
  )
  ...
  for lang in _SUPPORTED_LANGUAGES:
      ...
  ```
  Source the list from `runtime.catalog().records` distinct languages so
  it stays in sync as v1.x adds languages — better than hardcoding.

**Refactor opportunities**:
- Promote `_SUPPORTED_LANGUAGES` to a runtime helper
  `runtime.supported_languages_iter()` so future plugin additions register
  automatically.

**Fixture needs**: none (probe runs against the test's `tmp_path` workspace
root; pool returns "not_started" for unconfigured langs).
**Acceptance**: 4 RED tests pass.
**Effort**: S
**Risk**: low — purely additive.
**Gitflow**: `feature/v1.6-workspace-health-all-langs` → develop → main;
tag `v1.6-p3-workspace-health`

### Plan 11: `scalpel_rename` — honor `also_in_strings`

**Goal**: When `also_in_strings=True`, augment the LSP rename WorkspaceEdit
with grep-based string-literal replacements (similar to `scalpel_facades.py:_augment_workspace_edit_with_all_update`).

**RED tests** (extend `test/spikes/test_stage_2a_t5_rename.py`):

1. `test_rename_also_in_strings_replaces_string_literal_occurrences` —
   fixture with `def foo(): print("foo")` ; rename `foo→bar` with
   `also_in_strings=True`; assert resulting file contains
   `print("bar")`.
2. `test_rename_also_in_strings_default_false_leaves_strings_unchanged` —
   regression guard.
3. `test_rename_also_in_strings_skips_non_word_string_matches` — string
   `"foobar"` should NOT be replaced (substring, not whole-word).

**GREEN code changes**:

- `scalpel_facades.py:708`: remove `also_in_strings` from the `del` line.
- After `_augment_workspace_edit_with_all_update`, add:
  ```python
  if also_in_strings:
      workspace_edit = _augment_workspace_edit_with_string_literals(
          workspace_edit=workspace_edit, files=...,
          old_name=name_path.split("::")[-1].split(".")[-1],
          new_name=new_name,
      )
  ```
- New helper `_augment_workspace_edit_with_string_literals` modeled after
  `_augment_workspace_edit_with_all_update:857`.

**Refactor opportunities**:
- Both `_augment_*` helpers walk the workspace; consolidate into a single
  `augment_workspace_edit_with_text_search(edit, kind, ...)` strategy.

**Fixture needs**: small Python fixture with string-literal `"foo"` reference.
**Acceptance**: 3 RED tests pass.
**Effort**: M
**Risk**: medium — string-literal substitution is naïve; could rewrite
unintended matches. Mitigate via whole-word boundary in the regex.
**Gitflow**: `feature/v1.6-rename-also-in-strings` → develop → main; tag
`v1.6-p3-rename-strings`

### Plan 12: `scalpel_generate_constructor` + `scalpel_override_methods` — Phase 2.5 close

**Goal**: Wire `include_fields` / `method_names` to jdtls via
`coord.execute_command` (jdtls exposes `java.action.organizeImports.command`
shape). If jdtls's command surface doesn't accept per-field selection,
opener-tag the parameters informational and remove the "Phase 2.5"
deferral comment.

**RED tests** (extend `test/serena/refactoring/test_scalpel_generate_constructor.py`):

1. `test_generate_constructor_threads_include_fields_to_jdtls_when_advertised` —
   patch `coord.execute_command_allowlist` to include the relevant jdtls
   command; assert `coord.execute_command` was called with `include_fields`.
2. `test_generate_constructor_falls_back_to_default_when_command_missing` —
   no command in allowlist; assert codeaction path AND warning surfaces.
3. Symmetric tests for `override_methods.method_names`.

**GREEN code changes**:

- `scalpel_facades.py:3098-3100`: replace the Phase-2.5 deferral comment
  with one of two paths:
  - **Threading**: `if "java.organizeFields" in coord.execute_command_allowlist: ...`
  - **Opener-tag**: prepend the docstring with `Note: include_fields= is
    informational; jdtls's source.generate.constructor codeaction includes
    all non-static fields by default.`
- Symmetric at `:3153-3155`.

**Refactor opportunities**:
- `_java_generate_dispatch:2982` could grow an `extra_args` parameter for
  the threaded case.

**Fixture needs**: existing Java fixtures.
**Acceptance**: 6 RED tests pass.
**Effort**: M (threading) or S (opener-tag)
**Risk**: medium — jdtls command surface is fragile.
**Gitflow**: `feature/v1.6-java-phase-2-5-close` → develop → main; tag
`v1.6-p3-java-phase-2-5`

---

## P3 — Cosmetic (1 PR, all 43 facades)

### Plan 13: A5 — Examples blocks across all 43 facades

**Goal**: Append an `Examples:` block to every facade (33) and primitive
(10) docstring with one minimal `>>> tool.apply(...)` invocation. Use
existing test fixtures as the source of truth so examples are guaranteed
non-stale.

**RED tests** (`test/integration/test_facade_examples_block.py`):

1. `test_every_facade_has_examples_block` — parametrized over the 33
   facades + 10 primitives; assert `"Examples:" in ScalpelXxxTool.__doc__`.
2. `test_every_facade_examples_block_passes_doctest` — gated parametrize;
   `doctest.testmod(...)` on each example. Skip when fixture path is not
   resolvable in CI.

**GREEN code changes**:

- 43 docstring edits, each appending:
  ```
  Examples:
      >>> tool.apply(
      ...     file="src/lib.py",
      ...     position={"line": 10, "character": 4},
      ...     ...,
      ... )
      # returns JSON RefactorResult with applied=True and a checkpoint_id
  ```
- For each facade, source the example arguments from the facade's
  representative test in `test/spikes/test_stage_*` to ensure non-staleness.
- Add a CI gate: `test_facade_docstring_examples_drift` which loads the
  example block, parses the `>>> tool.apply(...)` line, and confirms the
  argument shape matches `inspect.signature(tool.apply)`.

**Refactor opportunities**:
- Single utility `extract_example_from_test(test_module_path)` that codes
  the staleness check.

**Fixture needs**: none (re-using existing test fixtures).

**Acceptance**:
- All 43 facades carry Examples blocks.
- The drift CI gate runs and is green.

**Effort**: M (mechanical 43 edits + 1 CI gate)
**Risk**: low — docstrings only.
**Gitflow**: `feature/v1.6-examples-cosmetic` → develop → main; tag
`v1.6-p3-examples`

---

## Cross-cutting refactors

### Refactor 1 (DRY, prerequisite for Plans 1-2-3): `apply_and_checkpoint(edit) -> str` helper

The 5-line snippet
```python
edit = _resolve_winner_edit(coord, action)
if isinstance(edit, dict) and edit:
    _apply_workspace_edit_to_disk(edit)
else:
    edit = {"changes": {}}
cid = record_checkpoint_for_workspace_edit(workspace_edit=edit, snapshot={})
```
appears at:
- `scalpel_facades.py:351-356` (`_split_rust`)
- `scalpel_facades.py:526-531` (`_extract`)
- `scalpel_facades.py:648-653` (`_inline`)
- `scalpel_facades.py:1029-1037` (`_imports_organize`)
- `scalpel_facades.py:1156-1163` (`_dispatch_single_kind_facade`)
- `scalpel_facades.py:1371-1379` (`_tidy_structure`)
- `scalpel_facades.py:1905-1912` (`_python_dispatch_single_kind`)
- `scalpel_facades.py:2249-2254` (`_fix_lints`)
- `scalpel_facades.py:3045-3051` (`_java_generate_dispatch`)

That's 9 sites with the same incantation. After Plan 4 (snapshot capture)
this becomes a 7-line snippet. **Lift to** `facade_support.py`:

```python
def apply_action_and_checkpoint(coord, action) -> tuple[str, dict[str, Any]]:
    """Resolve winner, apply to disk, capture snapshot, record checkpoint.
    Returns (checkpoint_id, applied_edit). Used by every dispatcher."""
    from .scalpel_facades import _resolve_winner_edit, _apply_workspace_edit_to_disk
    edit = _resolve_winner_edit(coord, action)
    if isinstance(edit, dict) and edit:
        snapshot = capture_pre_edit_snapshot(edit)
        _apply_workspace_edit_to_disk(edit)
    else:
        edit = {"changes": {}}
        snapshot = {}
    cid = record_checkpoint_for_workspace_edit(
        workspace_edit=edit, snapshot=snapshot,
    )
    return cid, edit
```

Sequence: land Plans 1-4 first using the duplicated snippet, then refactor
in Plan 14 (a follow-up) to consolidate. Or land the helper as part of
Plan 4 and have Plans 1-3-A use it from day 1 (preferred — saves a
re-edit pass).

### Refactor 2 (KISS): break the `scalpel_primitives` ↔ `scalpel_facades` import cycle

Plans 1, 3-A, 5 all need to import `_apply_workspace_edit_to_disk` /
`_FACADE_DISPATCH` from `scalpel_facades` into `scalpel_primitives`. Each
introduces a lazy-import-at-call-site, which is fragile.

Cleaner: move shared appliers (`_apply_workspace_edit_to_disk`,
`_apply_text_edits_to_file_uri`, `_uri_to_path`) to `facade_support.py`.
This needs no behavior change and is 100% test-preserving — lift in a
single PR before any of P1 starts.

### Refactor 3 (TRIZ "segmentation"): explicit "informational" parameter convention

Currently the `del param  # comment` pattern is invisible to docstring
introspection. Define a class-level decorator or simple convention:

```python
class ScalpelChangeReturnTypeTool(Tool):
    INFORMATIONAL_PARAMS: ClassVar[tuple[str, ...]] = ("new_return_type",)
    ...
```

Then the existing `attach_apply_source` machinery can surface this in
`scalpel_capabilities_list` so the LLM sees which params are routing-only.
Out of scope for v1.6; recommend v1.7.

---

## Test-fixture additions summary

| Path | Purpose | Plans using it |
|---|---|---|
| `test/fixtures/rust_extract_module_min/` | RA `refactor.extract.module` round-trip | 1, 7 |
| `test/fixtures/rust_extract_module_min/lib.rs` | 12-line source | 1, 7 |
| `test/fixtures/rust_extract_module_min/Cargo.toml` | Cargo manifest | 1, 7 |
| `test/fixtures/python_split_file/calcpy.py` (extend) | 4 functions for symbol-list test | 2 |
| `test/fixtures/python_split_file/expected_post_split/helpers.py` | Golden post-split | 2 |
| `test/fixtures/rollback_round_trip/calc.py` | Round-trip rollback | 3, 4 |
| `test/fixtures/rollback_resource_ops/` | Resource-op rollback | 3 |
| `test/fixtures/rename_strings/foo_with_strings.py` | also_in_strings | 11 |

---

## Summary table

| # | Facade | Verdict | Effort | Risk | PR | Branch | Tag |
|---|---|---|---|---|---|---|---|
| 1 | `scalpel_apply_capability` | STUB-P1 | M | medium | 1 | `feature/v1.6-fix-apply-capability` | `v1.6-p1-apply-capability` |
| 2 | `scalpel_split_file._split_python` | STUB-P1 | M | medium | 2 | `feature/v1.6-fix-split-python` | `v1.6-p1-split-python` |
| 3a | `scalpel_rollback` (path A) | STUB-P1 | L | high | 3 | `feature/v1.6-fix-rollback-real-applier` | `v1.6-p1-rollback` |
| 3b | `scalpel_rollback` (path B) | STUB-P3 | S | low | 3-alt | `feature/v1.6-rollback-warning-only` | `v1.6-p3-rollback-warning` |
| 4 | snapshot-capture cross-cut | STUB-P1 | M | medium | 4 | `feature/v1.6-fix-snapshot-capture` | `v1.6-p1-snapshot-capture` |
| 5 | `scalpel_dry_run_compose` | STUB-P1 | L | medium | 5 | `feature/v1.6-fix-dry-run-one-step` | `v1.6-p1-dry-run-real` |
| 6 | informational batch (×12) | HYBRID-P2 | M | low | 6 | `feature/v1.6-informational-param-batch` | `v1.6-p2-informational-batch` |
| 7 | `scalpel_split_file._split_rust` | HYBRID-P2 | M | medium | 7 | `feature/v1.6-split-rust-groups` | `v1.6-p2-split-rust` |
| 8 | `scalpel_expand_macro` | HYBRID-P2 | S | low | 8 | `feature/v1.6-expand-macro-dry-run` | `v1.6-p2-expand-macro` |
| 9 | `scalpel_verify_after_refactor` | HYBRID-P2 | S | low | 9 | `feature/v1.6-verify-after-refactor-dry-run` | `v1.6-p2-verify-after-refactor` |
| 10 | `scalpel_workspace_health` | HYBRID-P3 | S | low | 10 | `feature/v1.6-workspace-health-all-langs` | `v1.6-p3-workspace-health` |
| 11 | `scalpel_rename` | HYBRID-P3 | M | medium | 11 | `feature/v1.6-rename-also-in-strings` | `v1.6-p3-rename-strings` |
| 12 | Java Phase 2.5 (×2) | HYBRID-P3 | M | medium | 12 | `feature/v1.6-java-phase-2-5-close` | `v1.6-p3-java-phase-2-5` |
| 13 | A5 Examples (×43) | A5-cosmetic | M | low | 13 | `feature/v1.6-examples-cosmetic` | `v1.6-p3-examples` |
| R1 | `apply_and_checkpoint` helper | refactor | S | low | 14 | `feature/v1.6-refactor-apply-helper` | `v1.6-p3-refactor-apply-helper` |
| R2 | break import cycle | refactor | S | low | 0 (pre) | `feature/v1.6-refactor-break-cycle` | `v1.6-p1-refactor-break-cycle` |

**Suggested sequencing**:
1. R2 (break cycle) — unblocks Plans 1, 3-A, 5
2. Plan 4 (snapshot capture) — unblocks Plan 3-A
3. Plan 1 (apply_capability) — highest LLM-router visibility
4. Plan 2 (split_python) — second-highest correctness gap
5. Plan 3-A (rollback real) — depends on Plan 4
6. Plan 5 (dry_run_compose) — caps the P1 stubs
7. Plans 8, 9 (small dry_run fixes) — quick wins, parallel
8. Plan 6 (informational batch) — single-PR uniform fix
9. Plans 7, 10, 11, 12 (HYBRID contract fixes) — sequenced as developer
   bandwidth allows
10. Plan 13 (Examples cosmetic) — final polish, parallel-safe with anything
11. R1 (apply helper consolidation) — final DRY pass

---

## Coverage check vs. audit

| Audit row | Verdict | Plan | Status |
|---|---|---|---|
| 1 split_file (Py) | STUB | 2 | covered |
| 2 split_file (Rs) | HYBRID | 7 | covered |
| 3 extract | HYBRID | 6 | covered (informational) |
| 4 inline | HYBRID | 6 (+ optional 6-bonus for name_path threading) | covered |
| 5 rename | HYBRID | 11 | covered |
| 6 imports_organize | HYBRID | 6 | covered |
| 7 convert_module_layout | INTENTIONAL | 13 (Examples) | covered |
| 8 change_visibility | HYBRID | 6 | covered |
| 9 tidy_structure | HYBRID | 6 (with scope threading) | covered |
| 10 change_type_shape | INTENTIONAL | 13 | covered |
| 11 change_return_type | HYBRID | 6 | covered |
| 12 complete_match_arms | INTENTIONAL | 13 | covered |
| 13 extract_lifetime | HYBRID | 6 | covered |
| 14 expand_glob_imports | INTENTIONAL | 13 | covered |
| 15 generate_trait_impl_scaffold | HYBRID | 6 | covered |
| 16 generate_member | INTENTIONAL | 13 | covered |
| 17 expand_macro | HYBRID | 8 | covered |
| 18 verify_after_refactor | HYBRID | 9 | covered |
| 19 convert_to_method_object | INTENTIONAL | 13 | covered |
| 20 local_to_field | INTENTIONAL | 13 | covered |
| 21 use_function | INTENTIONAL | 13 | covered |
| 22 introduce_parameter | HYBRID | 6 | covered |
| 23 generate_from_undefined | HYBRID | 6 (with `target_kind` threading) | covered |
| 24 auto_import_specialized | HYBRID | 6 | covered |
| 25 fix_lints | HYBRID | 6 | covered |
| 26 ignore_diagnostic | HYBRID | 6 (with `rule` threading) | covered |
| 27 convert_to_async | INTENTIONAL | 13 | covered |
| 28 annotate_return_type | INTENTIONAL | 13 | covered |
| 29 convert_from_relative_imports | INTENTIONAL | 13 | covered |
| 30 rename_heading | INTENTIONAL | 13 | covered |
| 31 split_doc | INTENTIONAL | 13 | covered |
| 32 extract_section | INTENTIONAL | 13 | covered |
| 33 organize_links | INTENTIONAL | 13 | covered |
| 34 generate_constructor | HYBRID-P3 | 12 | covered |
| 35 override_methods | HYBRID-P3 | 12 | covered |
| 36 transaction_commit | INTENTIONAL | 13 | covered |
| 37 capabilities_list | INTENTIONAL | 13 | covered |
| 38 capability_describe | INTENTIONAL | 13 | covered |
| 39 apply_capability | STUB | 1 | covered |
| 40 dry_run_compose | STUB | 5 | covered |
| 41 confirm_annotations | INTENTIONAL | 13 | covered |
| 42 rollback | STUB | 3 | covered |
| 43 transaction_rollback | STUB | 3 | covered |
| 44 workspace_health | HYBRID-P3 | 10 | covered |
| 45 execute_command | INTENTIONAL | 13 | covered |
| 46 reload_plugins | INTENTIONAL | 13 | covered |
| 47 install_lsp_servers | INTENTIONAL | 13 | covered |

**Every audit row has a plan.** The 22 INTENTIONAL rows go through Plan 13
(Examples cosmetic) only, which the audit itself flagged as A5 universal.

---

## Author

AI Hive(R) over-planner. Sibling minimalist plan at
`docs/superpowers/plans/2026-04-29-stub-facade-fix/minimalist-plan.md`.
Synthesizer should reconcile.
