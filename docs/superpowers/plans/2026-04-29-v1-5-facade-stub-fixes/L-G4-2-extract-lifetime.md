# Leaf L-G4-2 — `ScalpelExtractLifetimeTool` honors `lifetime_name`

**Goal.** Stop discarding `lifetime_name` (`scalpel_facades.py:1576` `del preview_token, lifetime_name`). Mirrors L-G4-1 (HI-2) — same shape, different argument. After G1 lands, thread `lifetime_name` into `title_match`. When rust-analyzer's surfaced action title doesn't mention the requested lifetime, return `INPUT_NOT_HONORED`. Spec § HI-3.

**Strategy.** RA's `extract_lifetime` assist auto-picks a fresh lifetime name (`'a`, `'b`, ...). Caller-named lifetimes can't override the LSP's choice via the protocol; the title is the only honest seam. The fix is documented as a partial-honor: if the caller passes `lifetime_name="'session"` and RA suggests `'a`, the response is INPUT_NOT_HONORED. The user can accept RA's suggestion via `lifetime_name=None` or retry with a `title_match`-friendly value.

**Source spec.** § HI-3 (lines 62-64).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelExtractLifetimeTool.apply` (L1550-1589) | ~40 |
| `vendor/serena/test/spikes/test_v1_5_g4_2_extract_lifetime.py` | NEW | ~150 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_2_extract_lifetime.py`:

```python
"""v1.5 G4-2 — extract_lifetime honors lifetime_name (HI-3)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelExtractLifetimeTool
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
        "pub struct Holder { name: &str }\n"
    )
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelExtractLifetimeTool:
    tool = ScalpelExtractLifetimeTool.__new__(ScalpelExtractLifetimeTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title):
    a = MagicMock()
    a.id = action_id
    a.action_id = action_id
    a.title = title
    a.is_preferred = False
    a.provenance = "rust-analyzer"
    a.kind = "refactor.extract.lifetime"
    return a


def test_extract_lifetime_honors_named_lifetime(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [_action("ra:1", "Extract lifetime 'session")]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {
        "changes": {src.as_uri(): [{
            "range": {"start": {"line": 0, "character": 23},
                      "end": {"line": 0, "character": 24}},
            "newText": "<'session>",
        }]},
    }

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 23},
            lifetime_name="'session",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    assert "'session" in src.read_text(encoding="utf-8")


def test_extract_lifetime_input_not_honored_when_ra_picks_different(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [_action("ra:1", "Extract lifetime 'a")]

    fake_coord.merge_code_actions = _actions

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 23},
            lifetime_name="'session",
            language="rust",
        )
    payload = json.loads(out)
    assert payload.get("status") == "skipped"
    assert payload.get("reason") == "no_candidate_matched_title_match"
    # Source unchanged:
    assert src.read_text(encoding="utf-8") == "pub struct Holder { name: &str }\n"
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_2_extract_lifetime.py -x`.

## Implementation steps

1. **Drop `lifetime_name` from `del`** at `scalpel_facades.py:1576`.
2. **Pass `title_match=lifetime_name`** to `_dispatch_single_kind_facade(...)` in the delegation call.
3. **Update docstring** to acknowledge that RA's auto-pick may differ; INPUT_NOT_HONORED is the honest path.
4. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_2_extract_lifetime.py -x
uv run pytest vendor/serena/test/spikes/test_stage_3_t2_rust_wave_b.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(extract_lifetime): honor lifetime_name via title_match (HI-3)

Threads caller's lifetime_name into the shared dispatcher's title_match.
When RA picks a different lifetime, returns INPUT_NOT_HONORED instead of
silently applying.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** RA's title format `Extract lifetime 'X` may vary; substring match copes.
- **Rollback:** revert single commit; HI-3 reopens.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G7-A real-disk tests for extract_lifetime.

---

**Author:** AI Hive®.
