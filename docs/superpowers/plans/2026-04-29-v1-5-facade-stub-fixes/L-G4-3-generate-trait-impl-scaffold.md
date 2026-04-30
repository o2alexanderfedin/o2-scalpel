# Leaf L-G4-3 — `ScalpelGenerateTraitImplScaffoldTool` honors `trait_name`

**Goal.** Stop discarding the REQUIRED positional argument `trait_name` (`scalpel_facades.py:1666` `del preview_token, trait_name`). After G1 lands, this leaf threads `trait_name` into the dispatcher's `title_match` so the resolved action matches `Implement <trait_name>`. When no action matches, return `INPUT_NOT_HONORED` (current behavior silently scaffolds whatever RA's first trait is, which is plausible-looking nonsense). Spec § HI-4.

**Strategy.** Rust-analyzer's `generate_trait_impl` assist surfaces one action per "candidate trait near cursor"; the title format is stable: `Implement <trait_name> for <type>`. Title-substring match against `trait_name` is the right disambiguator. Because `trait_name` is REQUIRED at the type-signature level (positional `str`, no default), the upgrade from "decorative" to "honored" is most blast-radius-safe in this leaf — it's currently a SAFETY violation (caller asked for `Display`, got whatever RA proposes first).

**Source spec.** § HI-4 (lines 66-69).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelGenerateTraitImplScaffoldTool.apply` (L1641-1679) | ~40 |
| `vendor/serena/test/spikes/test_v1_5_g4_3_generate_trait_impl.py` | NEW | ~180 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_3_generate_trait_impl.py`:

```python
"""v1.5 G4-3 — generate_trait_impl_scaffold honors trait_name (HI-4)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelGenerateTraitImplScaffoldTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def rust_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "lib.rs"
    src.write_text("pub struct Foo;\n")
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelGenerateTraitImplScaffoldTool:
    tool = ScalpelGenerateTraitImplScaffoldTool.__new__(ScalpelGenerateTraitImplScaffoldTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title):
    a = MagicMock()
    a.id = action_id; a.action_id = action_id; a.title = title
    a.is_preferred = False; a.provenance = "rust-analyzer"
    a.kind = "refactor.rewrite.generate_trait_impl"
    return a


def test_generate_trait_impl_honors_named_trait(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [
            _action("ra:1", "Implement Debug for Foo"),
            _action("ra:2", "Implement Display for Foo"),
        ]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: (
        {"changes": {src.as_uri(): [{
            "range": {"start": {"line": 1, "character": 0},
                      "end": {"line": 1, "character": 0}},
            "newText": ("impl Display for Foo {\n"
                        "    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {\n"
                        "        todo!()\n    }\n}\n"),
        }]}}
        if aid == "ra:2" else None
    )

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 12},
            trait_name="Display",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    body = src.read_text(encoding="utf-8")
    assert "impl Display for Foo" in body
    assert "impl Debug" not in body


def test_generate_trait_impl_input_not_honored_when_unknown_trait(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [_action("ra:1", "Implement Debug for Foo")]

    fake_coord.merge_code_actions = _actions

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 12},
            trait_name="Display",
            language="rust",
        )
    payload = json.loads(out)
    assert payload.get("status") == "skipped"
    assert payload.get("reason") == "no_candidate_matched_title_match"
    assert src.read_text(encoding="utf-8") == "pub struct Foo;\n"
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_3_generate_trait_impl.py -x`.

## Implementation steps

1. **Drop `trait_name` from `del`** at `scalpel_facades.py:1666`.
2. **Pass `title_match=trait_name`** to `_dispatch_single_kind_facade(...)` in the delegation.
3. **Update docstring** — note that the dispatcher uses substring title match.
4. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_3_generate_trait_impl.py -x
uv run pytest vendor/serena/test/spikes/test_stage_3_t3_rust_wave_c.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(generate_trait_impl_scaffold): honor trait_name via title_match (HI-4)

Closes the safety gap where the REQUIRED trait_name positional was
discarded and RA's first proposed trait scaffolded silently.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** RA's title prefix may evolve. Mitigation: substring match is robust to "Implement" vs "Generate impl" prefixes.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G7-A real-disk tests for generate_trait_impl_scaffold.

---

**Author:** AI Hive®.
