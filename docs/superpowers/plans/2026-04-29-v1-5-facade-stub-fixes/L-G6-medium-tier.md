# Leaf L-G6 — MEDIUM tier sweep (ME-1 .. ME-7)

**Goal.** Address the seven MEDIUM-severity findings in one leaf with sub-checkboxes — they share a similar structural pattern (filter-after-dispatch, post-process, or substitute-before-apply) and are individually too small to justify their own leaf. Spec § ME-1 through ME-7.

**Sub-tasks (each = one logical fix; verified by its own focused test):**

| Sub | Spec | Subject | File:line | Strategy |
|---|---|---|---|---|
| ME-1 | `tidy_structure` `scope` discarded (L1325) | `scalpel_facades.py:1300-1363` | Filter `_TIDY_STRUCTURE_KINDS` by scope: `file` → all 3; `type` → `reorder_fields`; `impl` → `reorder_impl_items`. |
| ME-2 | `auto_import_specialized` `symbol_name` discarded (L2167) | `scalpel_facades.py:2139-2179` | Thread `title_match=symbol_name` to `_python_dispatch_single_kind` (G1). |
| ME-3 | `introduce_parameter` `parameter_name` discarded (L2074) | `scalpel_facades.py:2050-2086` | Post-process the WorkspaceEdit: regex-replace rope's auto-name (`p`, `param`) with `parameter_name`. Same pattern as L-G4-6's `new_name`. |
| ME-4 | `generate_constructor` / `override_methods` selection lists discarded (L3098, L3153) | `scalpel_facades.py:3098, 3153` | Phase-2.5 deferral acknowledged in spec; this leaf surfaces honestly via `INPUT_NOT_HONORED` envelope when the lists are non-empty. Update docstrings to match. (Wiring the jdtls interactive picker is post-v1.5.) |
| ME-5 | `convert_module_layout` `actions[0]` (L1201-1247) | `scalpel_facades.py:1201-1247` | Already uses shared dispatcher — once L-G1 lands, no change needed; the default-path uses `actions[0]` (status-quo). Marked sub-checkbox as "verified, no change". |
| ME-6 | `_java_generate_dispatch` (0,0) fallback may select wrong class (L3011-3019) | `scalpel_facades.py:2982-3064` | Replace the silent `(0,0)→(0,0)` fallback with `SYMBOL_NOT_FOUND` failure when `class_name_path` cannot be resolved. Closes the last HI-13 site. |
| ME-7 | `extract` `actions[0]` (covered by L-G1) + discarded knobs (covered by L-G4-6) | n/a | Verified-no-change after Wave 2; sub-checkbox confirms zero residual work. |

**Source spec.** § ME-1 through ME-7 (lines 117-142).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit ME-1, ME-2, ME-3, ME-4, ME-6 sites | ~150 |
| `vendor/serena/test/spikes/test_v1_5_g6_medium_tier.py` | NEW — one focused test per sub-task | ~400 |

## TDD — failing tests first (one per sub-task)

Create `vendor/serena/test/spikes/test_v1_5_g6_medium_tier.py` with seven tests, each named `test_me_<N>_<subject>`. Skeletons (full bodies follow the patterns established in G4 leaves):

```python
"""v1.5 G6 — MEDIUM tier sweep (ME-1 .. ME-7)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import (
    ScalpelTidyStructureTool,
    ScalpelAutoImportSpecializedTool,
    ScalpelIntroduceParameterTool,
    ScalpelGenerateConstructorTool,
    ScalpelOverrideMethodsTool,
    _java_generate_dispatch,
)
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


# --- ME-1: tidy_structure honors scope ----------------------------------

def test_me_1_tidy_structure_scope_impl_dispatches_only_reorder_impl_items(tmp_path):
    """scope='impl' must dispatch ONLY refactor.rewrite.reorder_impl_items
    (not sort_items or reorder_fields)."""
    src = tmp_path / "lib.rs"; src.write_text("impl Foo {}\n")
    tool = ScalpelTidyStructureTool.__new__(ScalpelTidyStructureTool)
    tool.get_project_root = lambda: str(tmp_path)
    fake_coord = MagicMock(); fake_coord.supports_kind.return_value = True
    captured: list[str] = []

    async def _actions(**kw):
        captured.append((kw.get("only") or [""])[0])
        return []

    fake_coord.merge_code_actions = _actions
    with patch("serena.tools.scalpel_facades.coordinator_for_facade", return_value=fake_coord):
        tool.apply(file=str(src), scope="impl", language="rust",
                   position={"line": 0, "character": 0})
    assert captured == ["refactor.rewrite.reorder_impl_items"], captured


# --- ME-2: auto_import_specialized honors symbol_name -------------------

def test_me_2_auto_import_specialized_threads_symbol_name_as_title_match(tmp_path):
    src = tmp_path / "calc.py"; src.write_text("x = compute()\n")
    tool = ScalpelAutoImportSpecializedTool.__new__(ScalpelAutoImportSpecializedTool)
    tool.get_project_root = lambda: str(tmp_path)
    fake_coord = MagicMock(); fake_coord.supports_kind.return_value = True

    a1 = MagicMock(); a1.id = "rope:1"; a1.action_id = "rope:1"
    a1.title = "from numpy import compute"; a1.kind = "quickfix.import"
    a1.is_preferred = False; a1.provenance = "pylsp-rope"
    a2 = MagicMock(); a2.id = "rope:2"; a2.action_id = "rope:2"
    a2.title = "from scipy import compute"; a2.kind = "quickfix.import"
    a2.is_preferred = False; a2.provenance = "pylsp-rope"

    async def _actions(**kw):
        return [a1, a2]
    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: (
        {"changes": {src.as_uri(): [{
            "range": {"start": {"line": 0, "character": 0},
                      "end": {"line": 0, "character": 0}},
            "newText": "from numpy import compute\n",
        }]}} if aid == "rope:1" else None
    )

    with patch("serena.tools.scalpel_facades.coordinator_for_facade", return_value=fake_coord):
        out = tool.apply(file=str(src),
                         position={"line": 0, "character": 4},
                         symbol_name="numpy",
                         language="python")
    payload = json.loads(out)
    assert payload["applied"] is True
    assert "from numpy" in src.read_text(encoding="utf-8")


# --- ME-3: introduce_parameter post-processes parameter_name ------------

def test_me_3_introduce_parameter_substitutes_caller_name(tmp_path):
    src = tmp_path / "calc.py"
    src.write_text("def f():\n    return 42\n")
    tool = ScalpelIntroduceParameterTool.__new__(ScalpelIntroduceParameterTool)
    tool.get_project_root = lambda: str(tmp_path)
    fake_coord = MagicMock(); fake_coord.supports_kind.return_value = True
    a = MagicMock(); a.id = "rope:1"; a.action_id = "rope:1"
    a.title = "Introduce parameter p"; a.kind = "refactor.rewrite.introduce_parameter"
    a.is_preferred = False; a.provenance = "pylsp-rope"

    async def _actions(**kw):
        return [a]
    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {
        "changes": {src.as_uri(): [{
            "range": {"start": {"line": 0, "character": 0},
                      "end": {"line": 1, "character": 0}},
            "newText": "def f(p=42):\n",
        }]},
    }

    with patch("serena.tools.scalpel_facades.coordinator_for_facade", return_value=fake_coord):
        out = tool.apply(file=str(src),
                         position={"line": 1, "character": 11},
                         parameter_name="answer",
                         language="python")
    payload = json.loads(out)
    assert payload["applied"] is True
    assert "answer=42" in src.read_text(encoding="utf-8")


# --- ME-4: generate_constructor + override_methods INPUT_NOT_HONORED ---

def test_me_4_generate_constructor_input_not_honored_when_include_fields_set(tmp_path):
    """When caller passes include_fields=['name'], jdtls picker isn't wired
    in v1.5 — surface honestly instead of silently using all fields."""
    src = tmp_path / "Foo.java"
    src.write_text("class Foo { String name; int age; }\n")
    tool = ScalpelGenerateConstructorTool.__new__(ScalpelGenerateConstructorTool)
    tool.get_project_root = lambda: str(tmp_path)
    out = tool.apply(file=str(src), class_name_path="Foo",
                     include_fields=["name"], language="java")
    payload = json.loads(out)
    # Honest: signal that include_fields wasn't honored.
    assert payload.get("status") == "skipped"
    assert "include_fields" in (payload.get("reason") or "")


# --- ME-6: java_generate_dispatch fails honestly on unresolvable class --

def test_me_6_java_generate_dispatch_fails_when_class_unresolvable(tmp_path):
    src = tmp_path / "Bar.java"; src.write_text("class Bar {}\n")
    fake_coord = MagicMock()

    async def _find(**kw):
        return None
    fake_coord.find_symbol_range = _find

    with patch("serena.tools.scalpel_facades.coordinator_for_facade", return_value=fake_coord):
        out = _java_generate_dispatch(
            stage_name="scalpel_test",
            file=str(src),
            class_name_path="Nonexistent",
            kind="source.generate.constructor",
            project_root=tmp_path,
            preview=False,
            allow_out_of_workspace=False,
        )
    payload = json.loads(out)
    assert payload["applied"] is False
    assert payload["failure"]["code"] == "SYMBOL_NOT_FOUND"


# Sub-tasks ME-5 and ME-7 are verified-no-change — covered by existing
# G1 / G4-6 regression suites; this leaf's commit notes the verification
# but doesn't add a redundant test.
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g6_medium_tier.py -x`.

## Implementation steps

1. **ME-1:** drop `del scope` at L1325; add a `_SCOPE_TO_KINDS` lookup; loop only the matched kinds.
2. **ME-2:** drop `del symbol_name` at L2167; pass `title_match=symbol_name` to `_python_dispatch_single_kind`.
3. **ME-3:** drop `del parameter_name` at L2074; reuse the `_post_process_extract_edit` pattern from L-G4-6 (lift to a shared `_substitute_auto_name` helper if not yet shared) to replace `\bp\b` → `parameter_name` in emitted hunks.
4. **ME-4:** in both `ScalpelGenerateConstructorTool.apply` and `ScalpelOverrideMethodsTool.apply`, when `include_fields` / `method_names` is non-empty, return `INPUT_NOT_HONORED` envelope before dispatch. Update docstrings to mark this as Phase-2.5 deferral. Empty / None list preserves today's behavior.
5. **ME-5:** verify-only — no code change.
6. **ME-6:** in `_java_generate_dispatch` (L3011-3019), replace the silent `(0,0)→(0,0)` fallback with `build_failure_result(code=SYMBOL_NOT_FOUND, ...)` when `find_symbol_range` returns None.
7. **ME-7:** verify-only — no code change.
8. **Submodule pyright clean** on the touched files.

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g6_medium_tier.py -x

# Regression sweeps:
uv run pytest vendor/serena/test/spikes/test_stage_3_t1_rust_wave_a.py \
                vendor/serena/test/spikes/test_stage_3_t4_python_wave_a.py \
                vendor/serena/test/spikes/test_stage_3_t5_python_wave_b.py \
                vendor/serena/test/integration/test_java_facades.py -x

uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(facade-medium): ME-1..ME-7 sweep — scope filter, title_match, post-process, honest envelopes

ME-1 tidy_structure scope filter; ME-2 auto_import title_match;
ME-3 introduce_parameter post-process; ME-4 generate_constructor +
override_methods surface INPUT_NOT_HONORED for selection lists;
ME-6 java_generate fails honestly on unresolvable class. ME-5 + ME-7
verified status-quo (covered by G1 / G4-6).

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** seven sub-tasks in one leaf risks merge conflicts if Wave 2 is in flight. Mitigation: G6 lands AFTER all G4-* leaves per the README's Wave 2 ordering.
- **Rollback:** revert single commit; ME-1..ME-7 reopen.

## Dependencies

- **Hard:** L-G1 (ME-2 uses title_match).
- **Soft:** L-G4-6 (ME-3 reuses post-process helper if lifted).
- **Blocks:** L-G7-A (ME-1 fixture), L-G7-B (ME-2, ME-3 fixtures), L-G5 (ME-6 closes the last HI-13 site).

---

**Author:** AI Hive®.
