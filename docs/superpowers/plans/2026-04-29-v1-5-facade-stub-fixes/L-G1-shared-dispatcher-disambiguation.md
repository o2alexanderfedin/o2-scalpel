# Leaf L-G1 — Shared dispatcher candidate-disambiguation policy

**Goal.** Replace the silent `actions[0]` choice in `_dispatch_single_kind_facade` (`scalpel_facades.py:1102`) and `_python_dispatch_single_kind` (`scalpel_facades.py:1870`) with a three-step disambiguation policy: (1) prefer `is_preferred=True`; (2) match by `MergedCodeAction.title` against an optional caller-supplied `title_match` string; (3) fall back to `actions[0]` when neither rule fires AND only one candidate exists. When step 2 is requested but multiple candidates remain ambiguous, return a new `INPUT_NOT_HONORED`-shaped envelope. **This leaf MUST land alone, before any G4 leaf.** Spec § HI-1.

**Architecture.** Both dispatchers receive an optional `title_match: str | None` parameter (default `None`, preserving current behavior for callers that haven't yet been migrated). The 17 downstream Tool subclasses pass `None` initially; the 10 G4 leaves migrate one Tool at a time to pass a real `title_match`. The policy is implemented as a free function `_select_candidate_action` so both dispatchers share it; this is also reusable for future bespoke dispatchers (e.g. `_split_rust` after G3a).

**Tech stack.** Python 3.13, pydantic boundaries, pytest. No new dependencies. `MergedCodeAction` already carries `title: str` and `is_preferred: bool` (`vendor/serena/src/serena/refactoring/multi_server.py:64-83`).

**Source spec.** `docs/superpowers/specs/2026-04-29-facade-stub-audit.md` § HI-1 (lines 50-55).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit — add `_select_candidate_action`, thread `title_match` through both dispatchers | ~80 |
| `vendor/serena/src/serena/tools/scalpel_schemas.py` | edit — verify `ErrorCode` covers the new envelope; if not, add `MULTIPLE_CANDIDATES`. (Spec uses this label in HI-1; current enum at L22-34 does not include it; we add it.) | ~3 |
| `vendor/serena/test/spikes/test_v1_5_g1_dispatcher_disambiguation.py` | NEW — unit tests for the policy + integration with both dispatchers | ~250 |

**Cited line ranges from the spec / source:**
- `_dispatch_single_kind_facade` body that takes `actions[0]`: `scalpel_facades.py:1156` (`workspace_edit = _resolve_winner_edit(coord, actions[0])`).
- `_python_dispatch_single_kind` analogous line: `scalpel_facades.py:1905`.
- `MergedCodeAction.is_preferred`: `multi_server.py:81`.
- `MergedCodeAction.title`: `multi_server.py:78`.

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g1_dispatcher_disambiguation.py`:

```python
"""v1.5 G1 — shared-dispatcher disambiguation policy.

Asserts:
  * Default behavior (title_match=None, no is_preferred): first action wins
    (status quo — does not regress 17 existing callers).
  * is_preferred=True wins over a non-preferred earlier candidate.
  * title_match selects the candidate whose normalized title contains the
    substring (case-insensitive). Wins even over is_preferred.
  * title_match with multiple matching candidates returns the
    MULTIPLE_CANDIDATES envelope (status=skipped, kind, candidates list).
  * title_match with zero matching candidates returns the same envelope
    with reason="no_candidate_matched_title_match".
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import (
    _select_candidate_action,
    _dispatch_single_kind_facade,
)


def _action(action_id: str, title: str, *, preferred: bool = False):
    a = MagicMock()
    a.id = action_id
    a.action_id = action_id
    a.title = title
    a.is_preferred = preferred
    a.provenance = "rust-analyzer"
    return a


def test_select_default_returns_first_action():
    actions = [_action("a", "First"), _action("b", "Second")]
    chosen, status = _select_candidate_action(actions, title_match=None)
    assert chosen is actions[0]
    assert status is None


def test_select_is_preferred_wins_over_first():
    actions = [_action("a", "First"), _action("b", "Second", preferred=True)]
    chosen, status = _select_candidate_action(actions, title_match=None)
    assert chosen is actions[1]
    assert status is None


def test_select_title_match_wins_over_is_preferred():
    actions = [
        _action("a", "Change visibility to pub(crate)"),
        _action("b", "Change visibility to pub", preferred=True),
    ]
    chosen, status = _select_candidate_action(
        actions, title_match="pub(crate)",
    )
    assert chosen is actions[0]
    assert status is None


def test_select_title_match_case_insensitive_substring():
    actions = [_action("a", "Implement Display for Foo")]
    chosen, status = _select_candidate_action(actions, title_match="display")
    assert chosen is actions[0]
    assert status is None


def test_select_title_match_ambiguous_returns_envelope():
    actions = [
        _action("a", "Change visibility to pub(crate)"),
        _action("b", "Change visibility to pub(crate) and re-export"),
    ]
    chosen, status = _select_candidate_action(
        actions, title_match="pub(crate)",
    )
    assert chosen is None
    assert status is not None
    assert status["status"] == "skipped"
    assert status["reason"] == "multiple_candidates_matched_title_match"
    assert len(status["candidates"]) == 2


def test_select_title_match_no_match_returns_envelope():
    actions = [_action("a", "Change visibility to pub")]
    chosen, status = _select_candidate_action(
        actions, title_match="pub(crate)",
    )
    assert chosen is None
    assert status is not None
    assert status["reason"] == "no_candidate_matched_title_match"


def test_dispatcher_default_path_unchanged_for_existing_callers(tmp_path):
    """Regression guard: 17 existing callers pass no title_match; their
    behavior must be byte-identical to the pre-G1 behavior — actions[0]
    chosen, edit applied, RefactorResult returned."""
    src = tmp_path / "lib.rs"
    src.write_text("fn x() {}\n")
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _fake_actions(**kw):
        return [_action("a", "Promote local to constant")]

    fake_coord.merge_code_actions = _fake_actions
    fake_coord.get_action_edit = lambda aid: {
        "changes": {
            src.as_uri(): [{
                "range": {"start": {"line": 0, "character": 0},
                          "end": {"line": 0, "character": 2}},
                "newText": "FN",
            }],
        },
    }
    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = _dispatch_single_kind_facade(
            stage_name="scalpel_test",
            file=str(src),
            position={"line": 0, "character": 0},
            kind="refactor.rewrite.promote_local_to_const",
            project_root=tmp_path,
            dry_run=False,
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    # Real-disk acid test:
    assert src.read_text(encoding="utf-8").startswith("FN")


def test_dispatcher_title_match_routes_to_correct_action(tmp_path):
    src = tmp_path / "lib.rs"
    src.write_text("pub fn x() {}\n")
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _fake_actions(**kw):
        return [
            _action("a", "Change visibility to pub"),
            _action("b", "Change visibility to pub(crate)"),
        ]

    fake_coord.merge_code_actions = _fake_actions

    def _resolve(aid):
        if aid == "b":
            return {
                "changes": {
                    src.as_uri(): [{
                        "range": {"start": {"line": 0, "character": 0},
                                  "end": {"line": 0, "character": 3}},
                        "newText": "pub(crate)",
                    }],
                },
            }
        return None  # 'a' resolution must NOT be requested.

    fake_coord.get_action_edit = _resolve
    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = _dispatch_single_kind_facade(
            stage_name="scalpel_change_visibility",
            file=str(src),
            position={"line": 0, "character": 0},
            kind="refactor.rewrite.change_visibility",
            project_root=tmp_path,
            dry_run=False,
            language="rust",
            title_match="pub(crate)",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    # The real-disk acid test: the edit that landed is the pub(crate) one.
    assert "pub(crate)" in src.read_text(encoding="utf-8")
```

Run `uv run pytest vendor/serena/test/spikes/test_v1_5_g1_dispatcher_disambiguation.py -x` — every test fails (module not yet wired). Stage tests only.

## Implementation steps

1. **Add `MULTIPLE_CANDIDATES` to `ErrorCode`** in `scalpel_schemas.py:22-34`. Conservative: append to the enum. (If we later decide it's better as a non-error envelope status, drop the enum addition; currently it's used only as a `status` discriminator string.)

2. **Add `_select_candidate_action` helper** in `scalpel_facades.py` near `_resolve_winner_edit` (around L1178). Signature:
   ```python
   def _select_candidate_action(
       actions: list[Any],
       *,
       title_match: str | None,
   ) -> tuple[Any | None, dict[str, object] | None]:
       """Returns (chosen_action, None) on success; (None, envelope) when
       title_match was requested but selection is ambiguous or empty."""
   ```
   Logic:
   - if `title_match` is `None`: prefer first `is_preferred=True`; else `actions[0]`.
   - if `title_match` is set: filter actions by case-insensitive substring match on `.title`. 0 hits → envelope `reason="no_candidate_matched_title_match"`; 1 hit → return it; ≥2 hits → envelope `reason="multiple_candidates_matched_title_match"`, include `candidates: [{id, title, provenance}, ...]` for caller debugging.

3. **Thread `title_match` through `_dispatch_single_kind_facade`** (`scalpel_facades.py:1102-1175`). Add `title_match: str | None = None` parameter. Replace `actions[0]` (L1156) with:
   ```python
   chosen, miss_envelope = _select_candidate_action(actions, title_match=title_match)
   if miss_envelope is not None:
       return json.dumps(miss_envelope)
   workspace_edit = _resolve_winner_edit(coord, chosen)
   ```

4. **Mirror in `_python_dispatch_single_kind`** (`scalpel_facades.py:1870-1924`). Same parameter, same replacement at L1905.

5. **Verify the 17 callers still compile** — they pass no `title_match` so default-path behavior is unchanged. Run the existing spike tests (`test_stage_3_t1_rust_wave_a.py` etc.); they must still PASS unmodified. This is the regression-protection step.

6. **Submodule pyright clean** on the touched files.

## Verification

```bash
# Failing test → green:
uv run pytest vendor/serena/test/spikes/test_v1_5_g1_dispatcher_disambiguation.py -x

# Regression guard — existing 17-caller tests:
uv run pytest vendor/serena/test/spikes/test_stage_3_t1_rust_wave_a.py \
                vendor/serena/test/spikes/test_stage_3_t2_rust_wave_b.py \
                vendor/serena/test/spikes/test_stage_3_t3_rust_wave_c.py \
                vendor/serena/test/spikes/test_stage_3_t4_python_wave_a.py \
                vendor/serena/test/spikes/test_stage_3_t5_python_wave_b.py -x

# pyright clean:
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py \
               vendor/serena/src/serena/tools/scalpel_schemas.py
```

**Atomic commit message draft:**

```
fix(facade-dispatch): add candidate-disambiguation policy to shared dispatchers (HI-1 root cause)

Replaces blind actions[0] selection with a three-step policy:
  1. is_preferred=True wins.
  2. title_match substring filter when caller supplies one.
  3. fall back to actions[0] preserving 17 existing callers' behavior.

Returns MULTIPLE_CANDIDATES envelope when title_match is ambiguous or has
zero hits — caller can audit candidates and pick a tighter title.

Closes spec § HI-1; precondition for L-G4-* parameter-graveyard fixes.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** the regression guard (step 5) catches a behavior delta in an existing caller. Cause would be that some caller depended on the side effect of `actions[0]` being chosen even when a later action was `is_preferred=True`. Mitigation: if found, revert the `is_preferred` rule to opt-in via a separate flag, or thread an explicit `prefer_is_preferred=False` into the migrated callers' invocations.
- **Rollback:** revert the single commit. The 17 G4 leaves cannot land without G1; the milestone is paused until G1 lands cleanly.

## Dependencies

- **Hard:** none. G1 is the substrate.
- **Blocks:** L-G3a (the bespoke `_split_rust` dispatcher will reuse `_select_candidate_action`), L-G4-1 through L-G4-10, L-G6 (ME-5 `convert_module_layout` title-disambig).

---

**Author:** AI Hive®.
