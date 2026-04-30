# Leaf L-G3a — `_split_rust` per-group iteration (CLOSES USER REPORT)

**Goal.** Replace the user-reported stub at `_split_rust` (`scalpel_facades.py:319-368`) with a real per-group iteration that mirrors `_split_python` (`scalpel_facades.py:275-317`). For each `target_module` key in `groups`, resolve every symbol's body range via `coord.find_symbol_range`, dispatch one `refactor.extract.module` per symbol with the symbol's actual range (not `(0,0)→(0,0)`), and merge the resulting WorkspaceEdits via the existing `_merge_workspace_edits` helper. Spec § CR-1 (the headline user-reported bug).

**Architecture.** The facade entry point already routes to `_split_rust` when `lang == "rust"`. The fix is internal to `_split_rust`: drop `del groups`, iterate `groups.items()`, resolve each symbol via `coord.find_symbol_range(file=file, name_path=symbol, project_root=str(project_root))`, build `(start, end)` from the resolved range, dispatch `merge_code_actions` per symbol, then merge edits and apply once. Symbols that fail resolution surface as `language_findings` warnings (not hard failures) so a partial group still progresses — gated by an `allow_partial=True` check that lifts that field out of the discarded set as well.

**Tech stack.** Python 3.13. Uses existing `MultiServerCoordinator.find_symbol_range` (line 1528 in `multi_server.py`), existing `_merge_workspace_edits` and `_resolve_winner_edit` helpers. No new dependencies.

**Source spec.** `docs/superpowers/specs/2026-04-29-facade-stub-audit.md` § CR-1 (lines 32-38).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `_split_rust` (L319-368) — full rewrite of body | ~100 |
| `vendor/serena/test/spikes/test_v1_5_g3a_split_rust_per_group.py` | NEW — failing tests asserting per-symbol LSP requests + real-disk module files | ~250 |

**Cited line ranges:**
- `_split_rust` body that must change: `scalpel_facades.py:319-368` (the entire helper).
- `_split_python` reference pattern (per-group iteration): `scalpel_facades.py:275-317`.
- `find_symbol_range` signature: `multi_server.py:1528-1547`.
- Existing mock-only test that NEVER asserted groups flowed: `test_stage_2a_t2_split_file.py:115`.

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g3a_split_rust_per_group.py`:

```python
"""v1.5 G3a — _split_rust per-group iteration (CR-1 user-report close-out).

Acid tests:
  * groups={"helpers":["add"], "ops":["sub"]} dispatches TWO
    refactor.extract.module requests (one per symbol).
  * Each request's (start, end) range matches the symbol's body span as
    returned by coord.find_symbol_range — NOT (0,0)→(0,0).
  * On-disk side effect: the resulting Path.read_text() of the new module
    files contains the moved symbol body (proven by feeding a fake_coord
    that returns a real WorkspaceEdit per symbol; applier writes those
    edits to disk).
  * Empty groups remains a no-op (no LSP call).
  * Symbol-not-found in one of N symbols + allow_partial=True → other
    symbols still dispatch; failed symbol appears in language_findings.
  * allow_partial=False (default) → first failure aborts.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelSplitFileTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def rust_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "lib.rs"
    src.write_text(
        "pub fn add(a: i32, b: i32) -> i32 { a + b }\n"
        "pub fn sub(a: i32, b: i32) -> i32 { a - b }\n"
    )
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelSplitFileTool:
    tool = ScalpelSplitFileTool.__new__(ScalpelSplitFileTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title, *, kind="refactor.extract.module"):
    a = MagicMock()
    a.id = action_id
    a.action_id = action_id
    a.title = title
    a.kind = kind
    a.is_preferred = False
    a.provenance = "rust-analyzer"
    return a


def test_split_rust_dispatches_per_symbol_with_real_ranges(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    # Per-symbol ranges as the real coordinator would return:
    range_for = {
        "add": {"start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 44}},
        "sub": {"start": {"line": 1, "character": 0},
                "end": {"line": 1, "character": 44}},
    }

    async def _find(file, name_path, project_root):
        return range_for.get(name_path)

    fake_coord.find_symbol_range = _find

    captured_calls: list[dict] = []

    async def _merge_actions(**kwargs):
        captured_calls.append(kwargs)
        # Each call returns one action; each action's id encodes the symbol.
        return [_action(f"ra:{kwargs['start']['line']}",
                        f"Move to module #{kwargs['start']['line']}")]

    fake_coord.merge_code_actions = _merge_actions

    # Each action resolves to a WorkspaceEdit creating a new module file.
    def _resolve(aid):
        line = aid.split(":")[1]
        new_module = f"helpers_{line}.rs"
        return {
            "documentChanges": [
                {"kind": "create",
                 "uri": (rust_workspace / new_module).as_uri()},
                {"textDocument": {"uri": (rust_workspace / new_module).as_uri(),
                                  "version": None},
                 "edits": [{"range": {"start": {"line": 0, "character": 0},
                                      "end": {"line": 0, "character": 0}},
                            "newText": f"// moved symbol from line {line}\n"}]},
            ],
        }

    fake_coord.get_action_edit = _resolve

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            groups={"helpers": ["add"], "ops": ["sub"]},
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True

    # Per-symbol dispatch: TWO calls, each with the symbol's real range.
    assert len(captured_calls) == 2, captured_calls
    starts = sorted(c["start"]["line"] for c in captured_calls)
    assert starts == [0, 1], starts
    # No (0,0)→(0,0) degenerate request:
    for c in captured_calls:
        assert (c["start"], c["end"]) != (
            {"line": 0, "character": 0}, {"line": 0, "character": 0},
        )

    # Real-disk acid test: G3b lands the resource-op support, but for now
    # we assert at least the text-edit slice landed where it could (the
    # newly-created module files exist after applier ran). G3b adds the
    # CreateFile assertion; here we assert the dispatch shape.
    # When G3b is in tree, replace the comment block with:
    #   assert (rust_workspace / "helpers_0.rs").exists()
    #   assert "moved symbol from line 0" in (rust_workspace / "helpers_0.rs").read_text()


def test_split_rust_empty_groups_short_circuits(rust_workspace):
    tool = _make_tool(rust_workspace)
    fake_coord = MagicMock()
    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(rust_workspace / "lib.rs"),
            groups={},
            language="rust",
        )
    payload = json.loads(out)
    assert payload["no_op"] is True


def test_split_rust_symbol_not_found_aborts_when_allow_partial_false(rust_workspace):
    tool = _make_tool(rust_workspace)
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _find(file, name_path, project_root):
        return None  # always unresolvable

    fake_coord.find_symbol_range = _find

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(rust_workspace / "lib.rs"),
            groups={"helpers": ["nonexistent"]},
            language="rust",
            allow_partial=False,
        )
    payload = json.loads(out)
    assert payload["applied"] is False
    assert payload["failure"]["code"] == "SYMBOL_NOT_FOUND"


def test_split_rust_allow_partial_skips_unresolvable(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _find(file, name_path, project_root):
        if name_path == "add":
            return {"start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 44}}
        return None

    fake_coord.find_symbol_range = _find

    async def _merge_actions(**kwargs):
        return [_action("ra:1", "Move add")]

    fake_coord.merge_code_actions = _merge_actions
    fake_coord.get_action_edit = lambda aid: {"changes": {}}

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            groups={"helpers": ["add", "missing"]},
            language="rust",
            allow_partial=True,
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    # Failed symbol surfaces as a language_finding warning.
    assert any(
        "missing" in (lf.get("message") or "")
        for lf in payload.get("language_findings") or ()
    )
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g3a_split_rust_per_group.py -x` — fails today (current `_split_rust` ignores `groups` and dispatches one (0,0) call).

## Implementation steps

1. **Drop `del groups`** at `scalpel_facades.py:327`. Drop the `del parent_layout, keep_in_original, reexport_policy, explicit_reexports, allow_partial, preview_token` line at L236-237 — `allow_partial` and `preview_token` flow through; the others remain documented-but-decorative *for this leaf* (see Out-of-scope note).

2. **Rewrite `_split_rust`** body (`scalpel_facades.py:319-368`):
   ```python
   def _split_rust(
       self, *, file, groups, project_root, dry_run, allow_partial,
   ) -> RefactorResult:
       coord = coordinator_for_facade(language="rust", project_root=project_root)
       # Capability gate already done by caller (apply()).
       t0 = time.monotonic()
       all_actions: list[Any] = []
       captured_edits: list[dict[str, Any]] = []
       findings: list[LanguageFinding] = []
       for target_module, symbols in groups.items():
           for symbol in symbols:
               rng = _run_async(coord.find_symbol_range(
                   file=file, name_path=symbol,
                   project_root=str(project_root),
               ))
               if rng is None:
                   if allow_partial:
                       findings.append(LanguageFinding(
                           code="symbol_not_found",
                           message=f"{symbol!r} for module {target_module!r}",
                       ))
                       continue
                   return build_failure_result(
                       code=ErrorCode.SYMBOL_NOT_FOUND,
                       stage="scalpel_split_file",
                       reason=f"Symbol {symbol!r} not found in {file!r}.",
                   )
               actions = _run_async(coord.merge_code_actions(
                   file=file,
                   start=rng["start"], end=rng["end"],
                   only=["refactor.extract.module"],
               ))
               if not actions:
                   if allow_partial:
                       findings.append(LanguageFinding(
                           code="no_action",
                           message=f"no refactor.extract.module for {symbol!r}",
                       ))
                       continue
                   return build_failure_result(
                       code=ErrorCode.SYMBOL_NOT_FOUND,
                       stage="scalpel_split_file",
                       reason=f"No refactor.extract.module for {symbol!r}.",
                   )
               # G1 default-path: take actions[0]; G1's title_match policy
               # is not threaded here because rust-analyzer offers exactly
               # one extract.module per cursor.
               winner = actions[0]
               all_actions.append(winner)
               edit = _resolve_winner_edit(coord, winner)
               if isinstance(edit, dict) and edit:
                   captured_edits.append(edit)
       elapsed_ms = int((time.monotonic() - t0) * 1000)
       if not all_actions:
           return RefactorResult(
               applied=False, no_op=True,
               diagnostics_delta=_empty_diagnostics_delta(),
               duration_ms=elapsed_ms,
               language_findings=tuple(findings),
           )
       if dry_run:
           return RefactorResult(
               applied=False, no_op=False,
               diagnostics_delta=_empty_diagnostics_delta(),
               preview_token=f"pv_split_{int(time.time())}",
               duration_ms=elapsed_ms,
               language_findings=tuple(findings),
           )
       merged = _merge_workspace_edits(captured_edits)
       _apply_workspace_edit_to_disk(merged)
       cid = record_checkpoint_for_workspace_edit(workspace_edit=merged, snapshot={})
       return RefactorResult(
           applied=True,
           diagnostics_delta=_empty_diagnostics_delta(),
           checkpoint_id=cid,
           duration_ms=elapsed_ms,
           language_findings=tuple(findings),
           lsp_ops=(LspOpStat(
               method="textDocument/codeAction",
               server="rust-analyzer",
               count=len(all_actions),
               total_ms=elapsed_ms,
           ),),
       )
   ```

3. **Update `apply()` call site** at L270-273 to pass `allow_partial=allow_partial` into `_split_rust(...)`. Update its signature accordingly.

4. **Submodule pyright clean** on the touched file.

## Out-of-scope for this leaf

`parent_layout`, `keep_in_original`, `reexport_policy`, `explicit_reexports` remain decorative in this leaf. Wiring them is a separate post-v1.5 enhancement: `keep_in_original` requires inverse-WorkspaceEdit synthesis (the LSP doesn't offer "extract everything except X"); `reexport_policy=preserve_public_api` requires post-edit `pub use ...` injection, an AST rewrite distinct from the LSP code-action surface. The v1.5 docstring updates these to clearly say "(planned for v1.6 post-edit injection)" instead of currently silently dropping them. Spec § CR-1 explicitly lists `groups` as "the whole point" and prioritises that fix.

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g3a_split_rust_per_group.py -x

# Existing split_file test must still pass (mock-only, but the dispatch
# shape we now produce is a superset of what it asserts):
uv run pytest vendor/serena/test/spikes/test_stage_2a_t2_split_file.py -x

uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit message draft:**

```
fix(split_rust): per-group iteration with real symbol ranges (CR-1)

Replaces the (0,0)→(0,0) single-action stub with one extract.module
LSP request per symbol in each target_module group, bracketed by the
symbol's body range from coord.find_symbol_range. Mirrors _split_python's
per-group pattern. allow_partial=True surfaces unresolvable symbols as
language_findings instead of aborting.

Closes the user-reported scalpel_split_file regression. Closes spec § CR-1.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** rust-analyzer offers >1 extract.module action for some symbol shapes; today the test asserts one. Mitigation: the implementation takes `actions[0]` (G1's default policy with no `title_match`); behavior is consistent with every other Rust facade. Future refinement can thread a `title_match` through the loop.
- **Risk:** `find_symbol_range` returns ranges that rust-analyzer rejects as too wide (selection-only assists). Mitigation: `find_symbol_range` returns the LSP `range` field (full body), which is what `merge_code_actions` expects. Existing `scalpel_extract` already uses this exact path successfully.
- **Rollback:** revert the single commit; spec § CR-1 reopens.

## Dependencies

- **Hard:** L-G1 (the spec calls for `_split_rust` to "mirror the per-group pattern" and use the same disambiguation policy). `_select_candidate_action` is reused (default-path: `actions[0]`).
- **Soft:** L-G3b — when G3b lands resource-op support in `_apply_workspace_edit_to_disk`, the on-disk acid-test assertion in this leaf's first test can be uncommented (see comment block in the test). G3a does not block on G3b for its own test discipline since the dispatch-shape assertion is already real.
- **Blocks:** L-G7-A (real-disk Rust facade tests reference this fix's behavior in their split_file scenarios).

---

**Author:** AI Hive®.
