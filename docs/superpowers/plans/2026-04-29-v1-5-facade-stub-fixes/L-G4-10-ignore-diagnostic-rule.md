# Leaf L-G4-10 — `ScalpelIgnoreDiagnosticTool` honors `rule`

**Goal.** Stop discarding `rule` (`scalpel_facades.py:2299` `del preview_token, rule, language`). Today the facade dispatches `quickfix.ruff_noqa` (or `quickfix.pyright_ignore`) and applies whatever quickfix the LSP returns first — silencing whichever rule the LSP picked, not the one the caller named. This leaf threads `rule` to the dispatcher's `title_match` so the `# noqa: <rule>` (or `# pyright: ignore[<rule>]`) comment matches the caller's request. Spec § HI-11.

**Strategy.** Both ruff and basedpyright emit one quickfix action per diagnostic; titles include the rule code (e.g. `Disable ruff: F401`, `Pyright: ignore reportMissingImports`). Title-substring match against `rule` is the right disambiguator.

**Source spec.** § HI-11 (lines 101-104).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelIgnoreDiagnosticTool.apply` (L2273-2321) | ~30 |
| `vendor/serena/test/spikes/test_v1_5_g4_10_ignore_diagnostic_rule.py` | NEW | ~180 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_10_ignore_diagnostic_rule.py`:

```python
"""v1.5 G4-10 — ignore_diagnostic honors rule (HI-11)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelIgnoreDiagnosticTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def python_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "main.py"
    src.write_text("import os\nx = 1\n")
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelIgnoreDiagnosticTool:
    tool = ScalpelIgnoreDiagnosticTool.__new__(ScalpelIgnoreDiagnosticTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title, kind):
    a = MagicMock()
    a.id = action_id; a.action_id = action_id; a.title = title
    a.kind = kind; a.is_preferred = False; a.provenance = "ruff"
    return a


def test_ignore_diagnostic_picks_rule_specific_action(python_workspace):
    tool = _make_tool(python_workspace)
    src = python_workspace / "main.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [
            _action("ruff:F401", "Disable F401: unused-import",
                    "quickfix.ruff_noqa"),
            _action("ruff:E501", "Disable E501: line-too-long",
                    "quickfix.ruff_noqa"),
        ]

    fake_coord.merge_code_actions = _actions

    def _resolve(aid):
        if aid == "ruff:F401":
            return {"changes": {src.as_uri(): [{
                "range": {"start": {"line": 0, "character": 9},
                          "end": {"line": 0, "character": 9}},
                "newText": "  # noqa: F401",
            }]}}
        return None  # E501 must NOT be resolved

    fake_coord.get_action_edit = _resolve

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 0},
            tool_name="ruff",
            rule="F401",
            language="python",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    body = src.read_text(encoding="utf-8")
    assert "# noqa: F401" in body
    assert "E501" not in body  # silenced rule did not leak


def test_ignore_diagnostic_input_not_honored_when_rule_missing(python_workspace):
    tool = _make_tool(python_workspace)
    src = python_workspace / "main.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [_action("ruff:E501", "Disable E501: line-too-long",
                        "quickfix.ruff_noqa")]

    fake_coord.merge_code_actions = _actions

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 0},
            tool_name="ruff",
            rule="F401",
            language="python",
        )
    payload = json.loads(out)
    assert payload.get("status") == "skipped"
    assert payload.get("reason") == "no_candidate_matched_title_match"
    assert src.read_text(encoding="utf-8") == "import os\nx = 1\n"
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_10_ignore_diagnostic_rule.py -x`.

## Implementation steps

1. **Drop `rule` from `del`** at `scalpel_facades.py:2299`.
2. **Pass `title_match=rule`** to `_python_dispatch_single_kind(...)` at L2316-2321.
3. **Update docstring** — note that title substring match is used; absent rule → INPUT_NOT_HONORED.
4. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_10_ignore_diagnostic_rule.py -x
uv run pytest vendor/serena/test/spikes/test_stage_3_t5_python_wave_b.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(ignore_diagnostic): honor rule via title_match (HI-11)

Threads caller's rule into shared dispatcher's title_match. Closes the
silent gap where the LSP-first quickfix was applied (silencing whichever
rule LSP returned first, not the one caller named).

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** ruff/pyright title formats vary. Mitigation: substring match copes; if observed format differs from "Disable F401" / "ignore reportMissingImports", adjust the substring expectation in the docstring.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G7-B real-disk tests for ignore_diagnostic.

---

**Author:** AI Hive®.
