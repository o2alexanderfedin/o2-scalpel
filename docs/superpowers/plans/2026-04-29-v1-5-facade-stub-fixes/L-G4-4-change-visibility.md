# Leaf L-G4-4 — `ScalpelChangeVisibilityTool` honors `target_visibility`

**Goal.** Stop discarding `target_visibility` (`scalpel_facades.py:1277` `del preview_token, target_visibility`). Today rust-analyzer cycles `pub` → `pub(crate)` → `pub(super)` → `private` and the caller can't pick a tier. After G1, this leaf maps `target_visibility` to RA's stable title format (`Change visibility to pub(crate)`, etc.) and threads that as `title_match`. Spec § HI-5.

**Strategy.** RA emits one action per visibility tier with a stable title format. The mapping is well-defined:

| `target_visibility` | RA title (substring sufficient) |
|---|---|
| `pub` | `pub` (but: `pub(crate)` and `pub(super)` are also matches — needs an exclusion) |
| `pub_crate` | `pub(crate)` |
| `pub_super` | `pub(super)` |
| `private` | `private` (or `to private`; substring `private` should suffice) |

To handle the `pub` ambiguity, we map `pub` → `Change visibility to pub` and rely on G1's MULTIPLE_CANDIDATES envelope when rust-analyzer offers both `pub` and `pub(crate)`; caller can refine via a more specific title. For the v1.5 starting set, use a small lookup table.

**Source spec.** § HI-5 (lines 71-74).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelChangeVisibilityTool.apply` (L1253-1290) — add `_VISIBILITY_TITLE_MATCH` table + thread title_match | ~50 |
| `vendor/serena/test/spikes/test_v1_5_g4_4_change_visibility.py` | NEW | ~200 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_4_change_visibility.py`:

```python
"""v1.5 G4-4 — change_visibility honors target_visibility (HI-5)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelChangeVisibilityTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def rust_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "lib.rs"
    src.write_text("fn helper() {}\n")
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelChangeVisibilityTool:
    tool = ScalpelChangeVisibilityTool.__new__(ScalpelChangeVisibilityTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title):
    a = MagicMock()
    a.id = action_id; a.action_id = action_id; a.title = title
    a.is_preferred = False; a.provenance = "rust-analyzer"
    a.kind = "refactor.rewrite.change_visibility"
    return a


def _three_visibility_actions():
    return [
        _action("ra:pub", "Change visibility to pub"),
        _action("ra:crate", "Change visibility to pub(crate)"),
        _action("ra:super", "Change visibility to pub(super)"),
    ]


def test_target_visibility_pub_crate_picks_correct_action(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return _three_visibility_actions()

    fake_coord.merge_code_actions = _actions

    def _resolve(aid):
        if aid == "ra:crate":
            return {"changes": {src.as_uri(): [{
                "range": {"start": {"line": 0, "character": 0},
                          "end": {"line": 0, "character": 2}},
                "newText": "pub(crate) fn",
            }]}}
        return None

    fake_coord.get_action_edit = _resolve

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 0},
            target_visibility="pub_crate",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    assert "pub(crate)" in src.read_text(encoding="utf-8")


def test_target_visibility_pub_super_picks_correct_action(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return _three_visibility_actions()

    fake_coord.merge_code_actions = _actions

    def _resolve(aid):
        if aid == "ra:super":
            return {"changes": {src.as_uri(): [{
                "range": {"start": {"line": 0, "character": 0},
                          "end": {"line": 0, "character": 2}},
                "newText": "pub(super) fn",
            }]}}
        return None

    fake_coord.get_action_edit = _resolve

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 0},
            target_visibility="pub_super",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    assert "pub(super)" in src.read_text(encoding="utf-8")
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_4_change_visibility.py -x`.

## Implementation steps

1. **Drop `target_visibility` from `del`** at `scalpel_facades.py:1277`.
2. **Add lookup table** near `_VISIBILITY_KIND` (L1250):
   ```python
   _VISIBILITY_TITLE_MATCH: dict[str, str] = {
       "pub_crate": "pub(crate)",
       "pub_super": "pub(super)",
       "private": "private",
       "pub": "pub",  # ambiguous — may surface MULTIPLE_CANDIDATES
   }
   ```
3. **Pass `title_match=_VISIBILITY_TITLE_MATCH.get(target_visibility)`** in the delegation call.
4. **Update docstring** — document the substring-match strategy + MULTIPLE_CANDIDATES path for `pub` when finer tiers are present.
5. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_4_change_visibility.py -x
uv run pytest vendor/serena/test/spikes/test_stage_3_t1_rust_wave_a.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(change_visibility): honor target_visibility via title_match (HI-5)

Maps {pub, pub_crate, pub_super, private} → RA stable title prefixes
and threads as title_match. Closes the silent-cycle bug where caller
could not pick a tier.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** ambiguity for `target_visibility="pub"` when RA also offers `pub(crate)`. Mitigation: G1's MULTIPLE_CANDIDATES envelope surfaces this explicitly; caller can audit candidates.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G7-A real-disk tests for change_visibility.

---

**Author:** AI Hive®.
